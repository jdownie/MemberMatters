import python_http_client.exceptions

from profile.models import Profile
from profile.xerohelpers import create_stripe_membership_invoice
from access.models import Doors, Interlock
from api_admin_tools.models import *

from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

import stripe
from services import canvas
from services.emails import send_email_to_admin
from constance import config
from membermatters.helpers import log_user_event
from django.db.utils import OperationalError
from sentry_sdk import capture_exception


class StripeAPIView(APIView):
    try:
        stripe.api_key = config.STRIPE_SECRET_KEY
    except OperationalError as error:
        capture_exception(error)


class MemberBucksAddCard(StripeAPIView):
    """
    get: gets the client secret used to add new card details.
    post: saves the customers card details.
    """

    def get(self, request):
        profile = request.user.profile
        customer_exists = True

        # check that the customer exists and isn't deleted
        if profile.stripe_customer_id:
            try:
                customer = stripe.Customer.retrieve(profile.stripe_customer_id)
                if customer.get("deleted") or not customer:
                    customer_exists = False

            except stripe.error.InvalidRequestError as error:
                # Invalid parameters were supplied to Stripe's API
                capture_exception(error)

                # if the customer doesn't exist then remove the Stripe customer id
                if error.http_status == 404:
                    profile.stripe_customer_id = None
                    profile.save()

                    customer_exists = False

        else:
            customer_exists = False

        if not customer_exists:
            try:
                log_user_event(
                    request.user, "Attempting to create stripe customer.", "stripe"
                )
                customer = stripe.Customer.create(
                    email=request.user.email,
                    name=profile.get_full_name(),
                    phone=profile.phone,
                )

                profile.stripe_customer_id = customer.id
                profile.save()

                log_user_event(
                    request.user,
                    f"Created stripe customer {request.user.profile.get_full_name()} (Stripe ID: {customer.id}).",
                    "stripe",
                )

                intent = stripe.SetupIntent.create(customer=profile.stripe_customer_id)

                return Response({"clientSecret": intent.client_secret})

            except stripe.error.StripeError as e:
                log_user_event(
                    request.user,
                    "Unknown stripe while saving payment details.",
                    "stripe",
                    request,
                )
                capture_exception(e)

                return Response(
                    {
                        "success": False,
                        "message": str(e),
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

            except Exception as e:
                log_user_event(
                    request.user,
                    "Unknown other error while saving payment details.",
                    "stripe",
                    request,
                )
                capture_exception(e)
                return Response(
                    {
                        "success": False,
                        "message": "Unknown error (unrelated to stripe).",
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

        else:
            intent = stripe.SetupIntent.create(customer=profile.stripe_customer_id)

            return Response({"clientSecret": intent.client_secret})

    def post(self, request):
        profile = request.user.profile
        payment_method_id = request.data.get("paymentMethodId")

        payment_method = stripe.PaymentMethod.retrieve(payment_method_id)

        profile.stripe_card_last_digits = payment_method["card"]["last4"]
        profile.stripe_card_expiry = f"{str(payment_method['card']['exp_month']).zfill(2)}/{str(payment_method['card']['exp_year'])}"
        profile.stripe_payment_method_id = payment_method_id
        profile.save()

        # attached the payment method to the customer
        stripe.PaymentMethod.attach(
            payment_method_id,
            customer=profile.stripe_customer_id,
        )
        # Set the default payment method on the customer
        stripe.Customer.modify(
            profile.stripe_customer_id,
            invoice_settings={
                "default_payment_method": payment_method_id,
            },
        )

        subject = f"You just added a payment card to your {config.SITE_OWNER} account."

        try:
            request.user.email_notification(
                subject,
                subject,
                subject,
                "Don't worry, your card details are stored safe "
                "with Stripe and are not on our servers. You "
                "can remove this card at any time via the "
                f"{config.SITE_NAME}.",
            )
        except python_http_client.exceptions.UnauthorizedError as e:
            capture_exception(e)
            return Response(
                {"message": "error.sendgridNotConfigured"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response()

    def delete(self, request):
        profile = request.user.profile

        if profile.stripe_payment_method_id:
            stripe.PaymentMethod.detach(profile.stripe_payment_method_id)

        profile.stripe_payment_method_id = ""
        profile.stripe_card_last_digits = ""
        profile.stripe_card_expiry = ""
        profile.save()
        return Response()


class MemberTiers(StripeAPIView):
    """
    get: gets a list of all member tiers.
    """

    def get(self, request):
        tiers = MemberTier.objects.filter(visible=True)
        formatted_tiers = []

        for tier in tiers:
            plans = []

            for plan in tier.plans.filter(visible=True):
                plans.append(plan.get_object())

            formatted_tiers.append(tier.get_object())

        return Response(formatted_tiers)


class PaymentPlanSignup(StripeAPIView):
    """
    post: attempts to sign the member up to a new membership payment plan.
    """

    def post(self, request, plan_id):
        current_plan = request.user.profile.membership_plan
        new_plan = PaymentPlan.objects.get(pk=plan_id)

        if current_plan:
            return Response({"success": False}, status=status.HTTP_409_CONFLICT)

        def create_subscription(attempts=0):
            attempts += 1

            if attempts > 3:
                log_user_event(
                    request.user,
                    "Too many attempts while creating subscription.",
                    "stripe",
                    "",
                )
                return Response(
                    {
                        "success": False,
                        "message": None,
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            try:
                return stripe.Subscription.create(
                    customer=request.user.profile.stripe_customer_id,
                    items=[
                        {"price": new_plan.stripe_id},
                    ],
                )

            except stripe.error.InvalidRequestError as e:
                capture_exception(e)
                error = e.json_body.get("error")

                if (
                    error["code"] == "resource_missing"
                    and "default payment method" in error["message"]
                ):
                    log_user_event(
                        request.user,
                        "InvalidRequestError (missing default payment method) from Stripe while creating subscription.",
                        "stripe",
                        error,
                    )

                    # try to set the default and try again
                    stripe.Customer.modify(
                        request.user.profile.stripe_customer_id,
                        invoice_settings={
                            "default_payment_method": request.user.profile.stripe_payment_method_id,
                        },
                    )

                    return create_subscription(attempts)

                if (
                    error["code"] == "resource_missing"
                    and "a similar object exists in live mode" in error["message"]
                ):
                    log_user_event(
                        request.user,
                        "InvalidRequestError (used test key with production object) from Stripe while "
                        "creating subscription.",
                        "stripe",
                        error,
                    )

                    return Response(
                        {
                            "success": False,
                            "message": error["message"],
                        },
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

                else:
                    log_user_event(
                        request.user,
                        "InvalidRequestError from Stripe while creating subscription.",
                        "stripe",
                        error,
                    )
                    return Response(
                        {
                            "success": False,
                            "message": None,
                        },
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

            except Exception as e:
                log_user_event(
                    request.user,
                    "InvalidRequestError from Stripe while creating subscription.",
                    "stripe",
                    e,
                )
                capture_exception(e)
                return Response(
                    {
                        "success": False,
                        "message": None,
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        new_subscription = create_subscription()

        try:
            if new_subscription.status == "active":
                request.user.profile.stripe_subscription_id = new_subscription.id
                request.user.profile.membership_plan = new_plan
                request.user.profile.subscription_status = "active"
                request.user.profile.save()

                log_user_event(
                    request.user,
                    "Successfully created subscription in Stripe.",
                    "stripe",
                    "",
                )

                return Response({"success": True})

            elif new_subscription.status == "incomplete":
                # if we got here, that means the subscription wasn't successfully created
                log_user_event(
                    request.user,
                    f"Failed to create subscription in Stripe with status {new_subscription.status}.",
                    "stripe",
                    "",
                )

                return Response(
                    {"success": True, "message": "signup.subscriptionFailed"}
                )

            else:
                log_user_event(
                    request.user,
                    f"Failed to create subscription in Stripe with status {new_subscription.status}.",
                    "stripe",
                    "",
                )
                return Response({"success": True})

        except KeyError as e:
            capture_exception(e)
            return new_subscription or e


class CanSignup(APIView):
    """
    get: checks if the member is eligible to signup, and what actions they need to complete.
    """

    def get(self, request):
        return Response(request.user.profile.can_signup())


class AssignAccessCard(APIView):
    """
    post: assigns the access card to the member.
    """

    def post(self, request):
        profile = request.user.profile
        profile.rfid = request.data["accessCard"]
        profile.save()

        return Response({"success": True})


class CheckInductionStatus(APIView):
    """
    post: checks if the member has completed the induction (via the canvas API).
    """

    def post(self, request):
        try:
            canvas_api = canvas.Canvas()
        except OperationalError as error:
            capture_exception(error)
            return Response({"success": False, "score": 0})

        if "induction" not in request.user.profile.can_signup()["requiredSteps"]:
            return Response({"success": True, "score": 0, "notRequired": True})

        try:
            score = canvas_api.get_student_score_for_course(
                config.INDUCTION_COURSE_ID, request.user.email
            )
            if score:
                induction_passed = score >= config.MIN_INDUCTION_SCORE

                if induction_passed:
                    request.user.profile.update_last_induction()

                    return Response({"success": True, "score": score})
            return Response({"success": False, "score": score})

        except Exception as e:
            capture_exception(e)
            return Response({"success": False, "score": 0, "error": str(e)})


def send_submitted_application_emails(member):
    subject = "Your membership application has been submitted"
    title = subject
    message = "Thanks for submitting your membership application! Your membership application has been submitted and you are now a 'member applicant'. Your membership will be officially accepted after 7 days, but we have granted site access immediately. You will receive an email confirming that your access card has been enabled. If for some reason your membership is rejected within this period, you will receive an email with further information."
    member.user.email_notification(subject, title, "", message)

    subject = f"A new person just became a member applicant: {member.get_full_name()}"
    title = subject
    message = f"{member.get_full_name()} just completed all steps required to sign up and is now a member applicant. Their site access has been enabled and membership will automatically be accepted within 7 days without objection from the executive."
    send_email_to_admin(subject, title, message)


class CompleteSignup(StripeAPIView):
    """
    post: completes the member's signup if they have completed all requirements and enables access
    """

    def post(self, request):
        member = request.user.profile
        signupCheck = member.can_signup()

        if member.subscription_status == "active":
            return Response({"success": False, "message": "signup.existingMember"})

        elif signupCheck["success"]:
            member.activate()
            send_submitted_application_emails(member)

            # give default door access
            for door in Doors.objects.filter(all_members=True):
                member.doors.add(door)

            # give default interlock access
            for interlock in Interlock.objects.filter(all_members=True):
                member.interlocks.add(interlock)

            member.user.email_welcome()

            return Response({"success": True})

        return Response(
            {
                "success": False,
                "message": "signup.requirementsNotMet",
                "items": signupCheck["requiredSteps"],
            }
        )


class SkipSignup(APIView):
    """
    post: skips the billing/tier signup process if they just want an account
    """

    def post(self, request):
        request.user.profile.set_account_only()

        return Response({"success": True})


class SubscriptionInfo(StripeAPIView):
    """
    get: retrieves information about the members subscription.
    """

    def get(self, request):
        current_plan = request.user.profile.membership_plan

        if not current_plan:
            return Response({"success": False})

        else:
            s = stripe.Subscription.retrieve(
                request.user.profile.stripe_subscription_id,
            )

            if s:
                subscription = {
                    "billingCycleAnchor": s.billing_cycle_anchor,
                    "currentPeriodEnd": s.current_period_end,
                    "cancelAt": s.cancel_at,
                    "cancelAtPeriodEnd": s.cancel_at_period_end,
                    "startDate": s.start_date,
                }
                return Response({"success": True, "subscription": subscription})

            return Response({"success": False})


class PaymentPlanResumeCancel(StripeAPIView):
    """
    post: attempts to cancel a member's payment plan.
    """

    def post(self, request, resume):
        current_plan = request.user.profile.membership_plan
        resume = True if resume == "resume" else False

        if not current_plan:
            return Response(
                {"success": False, "message": "paymentPlan.notExists"},
                status=status.HTTP_404_NOT_FOUND,
            )

        else:
            # this will modify the subscription to automatically cancel at the end of the current payment plan
            if resume:
                modified_subscription = stripe.Subscription.modify(
                    request.user.profile.stripe_subscription_id,
                    cancel_at_period_end=False,
                )

                if modified_subscription.cancel_at_period_end == False:
                    request.user.profile.subscription_status = "active"
                    request.user.profile.save()
                    return Response({"success": True})

            else:
                modified_subscription = stripe.Subscription.modify(
                    request.user.profile.stripe_subscription_id,
                    cancel_at_period_end=True,
                )

                if modified_subscription.cancel_at_period_end == True:
                    request.user.profile.subscription_status = "cancelling"
                    request.user.profile.save()
                    return Response({"success": True})

            return Response({"success": False})


class StripeWebhook(StripeAPIView):
    """
    post: processes a Stripe webhook event.
    """

    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        webhook_secret = config.STRIPE_WEBHOOK_SECRET
        body = request.body
        request_data = request.data

        if webhook_secret:
            # Retrieve the event by verifying the signature if webhook signing is configured.
            signature = request.headers.get("stripe-signature")
            try:
                event = stripe.Webhook.construct_event(
                    payload=body, sig_header=signature, secret=webhook_secret
                )
                data = event["data"]
            except Exception as e:
                print(e)
                capture_exception(e)
                return Response({"error": "Error validating Stripe signature."})

            # Get the type of webhook event sent - used to check the status of PaymentIntents.
            event_type = event["type"]
        else:
            data = request_data["data"]
            event_type = request_data["type"]

        data = data["object"]
        try:
            member = Profile.objects.get(stripe_customer_id=data["customer"])

        except Profile.DoesNotExist as e:
            capture_exception(e)
            return Response()

        # Just in case the linked Stripe account also processes other payments we should just ignore a non existent
        # customer.
        if not member:
            return Response()

        if event_type == "invoice.paid":
            invoice_status = data["status"]

            # If they aren't an active member, are allowed to signup, and have paid the invoice
            # then lets activate their account (this could be a new OR returning member)
            if (
                member.state != "active"
                and member.can_signup()["success"]
                and invoice_status == "paid"
            ):
                subject = "Your payment was successful."
                title = subject
                message = (
                    "Thanks for making a membership payment using our online payment system. "
                    "You've already met all of the requirements for activating your site access. Please check "
                    "for another email message confirming this was successful."
                )
                member.user.email_notification(subject, title, "", message)

                # set the subscription status to active
                member.subscription_status = "active"
                member.save()

                # activate their access card
                member.activate()
                member.user.email_enable_member()

            # If they aren't an active member, are NOT allowed to signup, and have paid the invoice
            # then we need to let them know and mark the subscription as active
            # (this could be a new OR returning member that's been too long since induction etc.)
            elif member.state != "active" and invoice_status == "paid":
                subject = "Your payment was successful."
                title = subject
                message = (
                    "Thanks for making a membership payment using our online payment system. "
                    "You haven't yet met all of the requirements for activating your site access. Once this "
                    "happens, you'll receive an email confirmation that your access card was activated. "
                    "If you are unsure how to proceed, or this email is unexpected, please contact us."
                )
                member.user.email_notification(subject, title, "", message)

                member.subscription_status = "active"
                member.save()

                # if this is a returning member then send the exec an email (new members have
                # already had this sent)
                if member.state != "noob":
                    send_submitted_application_emails(member)

            if member and config.STRIPE_CREATE_XERO_INVOICES:
                # check if the subscription is a membership subscription
                subscription = MemberTier.objects.get(stripe_id=data["subscription"])

                # return if the subscription is not a membership subscription
                if not subscription:
                    return Response()

                # get the charge object so we can check how much the Stripe fee was
                charge = stripe.Charge.retrieve(
                    data["charge"], expand=["balance_transaction"]
                )

                # grab the amount and the Stripe fee
                amount = charge.balance_transaction["amount"]
                fee = charge.balance_transaction["fee"]

                # generate a new Xero invoice
                create_stripe_membership_invoice(
                    user=member, amount=amount, fee_amount=fee
                )

            # in all other instances, we don't care about a paid invoice and can ignore it

        if event_type == "invoice.payment_failed":
            subject = "Your membership payment failed"
            title = subject
            preheader = ""
            message = (
                "Hi there, we tried to collect your membership payment via our online payment system but "
                "weren't successful. Please update your billing information via the member portal or contact "
                "us to resolve this issue. We'll try again, but if we're unable to collect your payment, your "
                "membership may be cancelled."
            )

            member.user.email_notification(subject, title, preheader, message)

        if event_type == "customer.subscription.deleted":
            # the subscription was deleted, so deactivate the member
            subject = "Your membership has been cancelled"
            title = subject
            preheader = ""
            message = (
                "You will receive another email shortly confirming that your access has been deactivated. Your "
                "membership was cancelled because we couldn't collect your payment, or you chose not to renew it."
            )

            member.user.email_notification(subject, title, preheader, message)
            member.deactivate()
            member.membership_plan = None
            member.stripe_subscription_id = None
            member.subscription_status = "inactive"
            member.save()

            subject = f"The membership for {member.get_full_name()} was just cancelled"
            title = subject
            message = (
                f"The Stripe subscription for {member.get_full_name()} ended, so their membership has "
                f"been cancelled. Their site access has been turned off."
            )
            send_email_to_admin(subject, title, message)

        return Response()
