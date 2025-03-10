<template>
  <div class="q-pa-md">
    <q-card class="register-card">
      <h6 class="q-ma-none q-pa-md">
        {{ $t("registrationCard.register") }}
      </h6>

      <q-card-section>
        <p class="q-pb-md">
          {{ $t("form.allFieldsRequired") }}
        </p>

        <q-form class="q-gutter-md" @submit="onSubmit" @reset="onReset">
          <q-input
            v-model="form.email"
            autofocus
            filled
            type="email"
            :label="$t('form.email')"
            lazy-rules
            :rules="[
              (val) => validateEmail(val) || $t('validation.invalidEmail'),
            ]"
          />

          <div class="row items-start no-wrap">
            <q-input
              v-model="form.firstName"
              class="q-pr-md"
              filled
              :label="$t('form.firstName')"
              lazy-rules
              :rules="[
                (val) =>
                  validateNotEmpty(val) || $t('validation.cannotBeEmpty'),
              ]"
            />
            <q-input
              v-model="form.lastName"
              filled
              :label="$t('form.lastName')"
              lazy-rules
              :rules="[
                (val) =>
                  validateNotEmpty(val) || $t('validation.cannotBeEmpty'),
              ]"
            />
          </div>

          <div class="row items-start no-wrap">
            <q-input
              v-model="form.screenName"
              class="q-pr-md"
              filled
              :label="$t('form.screenName')"
              lazy-rules
              :rules="[
                (val) =>
                  validateNotEmpty(val) || $t('validation.cannotBeEmpty'),
              ]"
            />
            <q-input
              v-model="form.mobile"
              filled
              type="tel"
              :label="$t('form.mobile')"
              lazy-rules
              :rules="[
                (val) =>
                  validateNotEmpty(val) || $t('validation.cannotBeEmpty'),
              ]"
            />
          </div>

          <q-input
            v-model="form.password"
            :label="$t('form.password')"
            filled
            :type="isPwd ? 'password' : 'text'"
            lazy-rules
            :rules="[
              (val) =>
                validateNotEmpty(val) || $t('validation.invalidPassword'),
            ]"
          >
            <template v-slot:append>
              <q-icon
                :name="isPwd ? icons.visibilityOff : icons.visibility"
                class="cursor-pointer"
                @click="isPwd = !isPwd"
              />
            </template>
          </q-input>

          <q-banner v-if="error" class="bg-negative text-white">
            {{ $t("error.requestFailed") }}
          </q-banner>

          <q-banner v-if="errorExists" class="bg-negative text-white">
            {{ $t(errorExists) }}
          </q-banner>

          <p class="text-caption">
            {{ $t("registrationCard.alreadyAMember") }}
            <router-link
              :to="{ name: 'login' }"
              :class="$q.dark.isActive ? 'text-white' : 'text-black'"
            >
              {{ $t("registrationCard.loginHere") }}
            </router-link>
          </p>

          <div class="row">
            <q-space />
            <q-btn
              :label="$t('button.submit')"
              type="submit"
              color="primary-btn"
              :loading="buttonLoading"
              :disable="buttonLoading"
            />
          </div>
        </q-form>
      </q-card-section>
    </q-card>
  </div>
</template>

<script>
import { mapGetters } from "vuex";
import formMixin from "../../mixins/formMixin";
import icons from "../../icons";

export default {
  name: "RegistrationCard",
  mixins: [formMixin],
  data() {
    return {
      failed: false,
      error: false,
      errorExists: false,
      complete: false,
      buttonLoading: false,
      isPwd: true,
      form: {
        firstName: null,
        lastName: null,
        email: null,
        screenName: null,
        mobile: null,
        password: null,
      },
    };
  },
  mounted() {
    if (this.loggedIn) this.$router.push({ name: "dashboard" });
  },
  computed: {
    ...mapGetters("profile", ["loggedIn"]),
    icons() {
      return icons;
    },
  },
  methods: {
    onReset() {
      this.email = null;
      this.password = null;
    },
    onSubmit() {
      this.register();
    },
    /**
     * This sends the registration API request to register the user.
     */
    register() {
      this.errorExists = false;
      this.error = false;
      this.buttonLoading = true;

      this.$axios
        .post("/api/register/", {
          firstName: this.form.firstName,
          lastName: this.form.lastName,
          email: this.form.email,
          screenName: this.form.screenName,
          mobile: this.form.mobile,
          password: this.form.password,
        })
        .then(() => {
          this.failed = false;
          this.error = false;
          this.complete = true;

          this.$router.push({ name: "registerSuccess" });
        })
        .catch((error) => {
          if (error.response.status === 409) {
            this.errorExists = error.response.data.message;
            this.error = false;
          } else {
            this.error = true;
            this.errorExists = false;
          }
        })
        .finally(() => {
          this.buttonLoading = false;
        });
    },
  },
};
</script>

<style scoped>
.register-card {
  width: 420px;
}
</style>
