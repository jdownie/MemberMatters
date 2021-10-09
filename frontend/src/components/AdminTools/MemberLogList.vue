<template>
  <div class="q-pl-lg q-pa-md">
    <q-tabs
      v-model="tab"
      dense
      class="text-grey"
      active-color="primary"
      indicator-color="primary"
      align="justify"
    >
      <q-tab name="doors" label="Doors" />
      <q-tab name="interlocks" label="Interlocks" />
    </q-tabs>

    <q-separator />

    <q-tab-panels v-model="tab" animated>
      <q-tab-panel name="doors">
        <div class="row flex content-start justify-center">
          <q-table
            :data="humanRecentDoorSwipes"
            :columns="[
              { name: 'user', label: 'User', field: 'user', sortable: true },
              { name: 'door', label: 'Door', field: 'name', sortable: true },
              {
                name: 'swipedAt',
                label: 'Swiped At',
                field: 'date',
                sortable: true,
              },
            ]"
            row-key="key"
            :filter="filter"
            :pagination.sync="doorPagination"
            :dense="$q.screen.lt.md"
            :grid="$q.screen.xs"
            class="table"
            :loading="loading"
          >
            <template v-slot:top-right>
              <q-input
                v-model="filter"
                outlined
                dense
                debounce="300"
                placeholder="Search"
              >
                <template v-slot:append>
                  <q-icon :name="icons.search" />
                </template>
              </q-input>
            </template>
          </q-table>
        </div>
      </q-tab-panel>

      <q-tab-panel name="interlocks">
        <div class="row flex content-start justify-center">
          <q-table
            :data="humanRecentInterlockSwipes"
            :columns="[
              {
                name: 'userOn',
                label: 'Turned On By',
                field: 'userOn',
                sortable: true,
              },
              {
                name: 'door',
                label: 'Interlock',
                field: 'name',
                sortable: true,
              },
              {
                name: 'sessionStart',
                label: 'Turned On At',
                field: 'sessionStart',
                sortable: true,
              },
              {
                name: 'userOff',
                label: 'Turned Off By',
                field: 'userOff',
                sortable: true,
              },
              {
                name: 'sessionEnd',
                label: 'Turned Off At',
                field: 'sessionEnd',
                sortable: true,
              },
            ]"
            row-key="key"
            :filter="filter"
            :pagination.sync="interlockPagination"
            :dense="$q.screen.lt.md"
            :grid="$q.screen.xs"
            :loading="loading"
          >
            <template v-slot:top-right>
              <q-input
                v-model="filter"
                outlined
                dense
                debounce="300"
                placeholder="Search"
              >
                <template v-slot:append>
                  <q-icon :name="icons.search" />
                </template>
              </q-input>
            </template>
          </q-table>
        </div>
      </q-tab-panel>
    </q-tab-panels>

    <refresh-data-dialog v-model="errorLoading" />
  </div>
</template>

<script>
import { mapActions, mapGetters } from "vuex";
import icons from "../icons";
import RefreshDataDialog from "./RefreshDataDialog";
import formatMixin from "src/mixins/formatMixin";

export default {
  name: "MemberLogList",
  components: { RefreshDataDialog },
  mixins: [formatMixin],
  props: {
    member: {
      type: String,
      default: ""
    },
  },
  data() {
    return {
      loading: false,
      errorLoading: false,
      updateInterval: null,
      filter: "",
      pagination: {
        sortBy: "date",
        descending: false,
        rowsPerPage: this.$q.screen.xs ? 3 : 8,
      },
    };
  },
  mounted() {
    this.loading = true;
    this.$axios
      .get(`/members/${}/logs/`)
      .catch(() => {
        this.errorLoading = true;
      })
      .finally(() => {
        this.loading = false;
      });
  },
  computed: {
    ...mapGetters("tools", ["recentSwipes"]),
    icons() {
      return icons;
    },
    humanRecentDoorSwipes() {
      /**
       * Returns an array of human readable logs.
       */
      if (this.recentSwipes.doors) {
        return this.recentSwipes.doors.map((value) => {
          return {
            key: value.user + value.date,
            user: value.user,
            date: this.formatDateSimple(value.date),
            name: value.name,
          };
        });
      }

      return [];
    },
  },
};
</script>

<style lang="stylus" scoped>
@media (max-width: $breakpoint-xs-max)
  .access-list
    width: 100%;
</style>
