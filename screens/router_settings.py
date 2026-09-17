from textual.containers import VerticalScroll, Horizontal
from textual.widgets import Static, Label, Input, Button, Select
from textual import work

from widgets.confirm_dialog import ConfirmDialog
from services import router as router_service
from services import system as system_service


class RouterSettingsPage(VerticalScroll):
    """Settings page: change the router's cellular APN and reboot the
    router if needed, plus sync the Nano's hardware clock (RTC) from its
    system clock. Talks to the router's own admin interface via the
    Nano (the laptop can't reach the router's LAN IP directly), by
    deploying and running router_settings.py on the Nano for each APN
    action.
    """

    def compose(self):

        yield Static("[bold]Router Settings[/bold]", classes="page-title")

        yield Static(
            "Changes are sent to the router's own admin interface via the "
            "Nano. A reboot is required for a new APN to actually take "
            "effect - saving alone stores it but keeps using the current "
            "one until the router restarts.",
            classes="info-block",
        )

        with Horizontal(classes="setting-inline-row"):
            yield Label("Current APN (SIM 1)")
            self.current_apn = Static("Loading...")
            yield self.current_apn

        with Horizontal(classes="setting-inline-row"):
            yield Label("Current APN (SIM 2)")
            self.current_apn2 = Static("-")
            yield self.current_apn2

        with Horizontal(classes="setting-inline-row"):
            yield Label("New APN")
            yield Input(placeholder="e.g. internet", id="apn_input", classes="settings-control")

        with Horizontal(classes="setting-inline-row"):
            yield Label("SIM Slot")
            yield Select(
                [("SIM 1", "1"), ("SIM 2", "2")],
                value="1",
                id="apn_sim_select",
                allow_blank=False,
            )

        with Horizontal(classes="setting-actions", id="router_settings_actions_row"):
            yield Button("Save APN", id="save_apn_button")
            yield Button("Save APN + Reboot", id="save_apn_reboot_button")
            yield Button("Reboot Router Only", id="reboot_only_button")

        self.status = Static("")
        yield self.status

        yield Static("", classes="section-divider")

        yield Static("[bold]Time Settings[/bold]", classes="page-title")

        yield Static(
            "If the hardware clock (RTC) has drifted or was never set, "
            "this writes the Nano's current system time into it. This "
            "doesn't fix a wrong system clock itself - it only copies "
            "whatever the system clock currently reads (check Date Time "
            "Info on the Dashboard first if you're not sure it's correct).",
            classes="info-block",
        )

        with Horizontal(classes="setting-actions"):
            yield Button("Sync RTC with Local Time", id="sync_rtc_button")

        self.rtc_status = Static("")
        yield self.rtc_status

        yield Static("", classes="section-divider")

        yield Static("[bold]LCD Settings[/bold]", classes="page-title")

        yield Static(
            "Controls whether the Nano's LCD shows its normal screens or "
            "a special admin menu. This reboots the Nano itself (the "
            "device the dashboard is connected to) - the connection "
            "will drop briefly and reconnect automatically once it's "
            "back up, the same way it recovers from any other temporary "
            "loss of connection.",
            classes="info-block",
        )

        with Horizontal(classes="setting-inline-row"):
            yield Label("Admin Menu State:")
            self.controller_state = Static("Loading...")
            yield self.controller_state

        with Horizontal(classes="setting-actions"):
            yield Button("Enable", id="enable_admin_menu_button")
            yield Button("Disable", id="disable_admin_menu_button")

        self.lcd_status = Static("")
        yield self.lcd_status

        # Trailing spacer: the last real widget above needs something
        # after it to scroll into view, otherwise it sits flush against
        # the bottom edge of the scroll area and can appear clipped.
        # This adds scrollable content height (unlike padding on the
        # container itself, which would shrink the visible viewport).
        yield Static("\n\n")

    def on_mount(self) -> None:
        self.refresh_apn()
        self.refresh_controller_state()

    def on_show(self) -> None:
        self.refresh_apn()
        self.refresh_controller_state()

    def force_refresh(self) -> None:
        self.refresh_apn()
        self.refresh_controller_state()

    def refresh_apn(self) -> None:
        self._fetch_apn()

    @work(thread=True, exclusive=True, group="router-settings-fetch")
    def _fetch_apn(self) -> None:
        apn = router_service.get_router_apn()
        self.app.call_from_thread(self._apply_apn, apn)

    def _apply_apn(self, apn) -> None:
        self.current_apn.update(apn.get("apn", "-") or "-")
        dualsim = apn.get("dualsim") not in ("", "0", None)
        self.current_apn2.update((apn.get("apn2", "-") or "-") if dualsim else "N/A (single SIM)")

    # ------------------------------------------------------------------

    def on_button_pressed(self, event) -> None:

        if event.button.id == "save_apn_button":
            self._save_apn(reboot=False)

        elif event.button.id == "save_apn_reboot_button":
            self._confirm_save_apn_reboot()

        elif event.button.id == "reboot_only_button":
            self._confirm_reboot_only()

        elif event.button.id == "sync_rtc_button":
            self._sync_rtc()

        elif event.button.id == "enable_admin_menu_button":
            self._confirm_set_controller_state(99, 99, "Enable Admin Menu")

        elif event.button.id == "disable_admin_menu_button":
            self._confirm_set_controller_state(1, 0, "Disable Admin Menu")

    def _get_new_apn(self):
        return self.query_one("#apn_input", Input).value.strip()

    def _get_sim(self):
        return int(self.query_one("#apn_sim_select", Select).value)

    def _save_apn(self, reboot: bool) -> None:

        new_apn = self._get_new_apn()

        if not new_apn:
            self.status.update("[#E05C5C]Enter an APN first[/#E05C5C]")
            return

        sim = self._get_sim()

        self._set_buttons_disabled(True)
        self.status.update(f"Saving APN ({new_apn}) for SIM {sim}...")
        self._apply_apn_change(new_apn, sim, reboot)

    def _confirm_save_apn_reboot(self) -> None:

        new_apn = self._get_new_apn()

        if not new_apn:
            self.status.update("[#E05C5C]Enter an APN first[/#E05C5C]")
            return

        sim = self._get_sim()

        def handle_result(confirmed: bool):
            if confirmed:
                self._set_buttons_disabled(True)
                self.status.update(f"Saving APN ({new_apn}) for SIM {sim} and rebooting router...")
                self._apply_apn_change(new_apn, sim, True)

        self.app.push_screen(
            ConfirmDialog(
                f"Save APN \"{new_apn}\" for SIM {sim} and reboot the router now?\n\n"
                "The router will be briefly unreachable (roughly 30-90s) while it restarts.",
                title="Reboot Router?",
                confirm_label="Save + Reboot",
            ),
            handle_result,
        )

    def _confirm_reboot_only(self) -> None:

        def handle_result(confirmed: bool):
            if confirmed:
                self._set_buttons_disabled(True)
                self.status.update("Rebooting router...")
                self._apply_reboot_only()

        self.app.push_screen(
            ConfirmDialog(
                "Reboot the router now? No settings will be changed.\n\n"
                "It will be briefly unreachable (roughly 30-90s) while it restarts.",
                title="Reboot Router?",
                confirm_label="Reboot",
            ),
            handle_result,
        )

    def _set_buttons_disabled(self, disabled: bool) -> None:
        self.query_one("#save_apn_button", Button).disabled = disabled
        self.query_one("#save_apn_reboot_button", Button).disabled = disabled
        self.query_one("#reboot_only_button", Button).disabled = disabled

    @work(thread=True, exclusive=True, group="router-settings-action")
    def _apply_apn_change(self, new_apn, sim, reboot) -> None:
        success, output = router_service.set_router_apn(new_apn, sim=sim, reboot=reboot)
        self.app.call_from_thread(self._show_action_result, success, output, reboot)

    @work(thread=True, exclusive=True, group="router-settings-action")
    def _apply_reboot_only(self) -> None:
        success, output = router_service.reboot_router()
        self.app.call_from_thread(self._show_action_result, success, output, True)

    def _show_action_result(self, success: bool, output: str, rebooted: bool) -> None:

        self._set_buttons_disabled(False)

        if success:
            note = " Router is restarting - it'll be back in roughly 30-90s." if rebooted else ""
            self.status.update(f"[#5FD68A]Done.{note}[/#5FD68A]")
            self.query_one("#apn_input", Input).value = ""
            self.refresh_apn()
        else:
            self.status.update(f"[#E05C5C]Failed: {output.strip()[:200]}[/#E05C5C]")

    # ------------------------------------------------------------------
    # Time Settings
    # ------------------------------------------------------------------

    def _sync_rtc(self) -> None:
        self.query_one("#sync_rtc_button", Button).disabled = True
        self.rtc_status.update("Syncing RTC with local time...")
        self._apply_rtc_sync()

    @work(thread=True, exclusive=True, group="router-settings-rtc")
    def _apply_rtc_sync(self) -> None:
        success, output = system_service.sync_rtc_from_system_clock()
        self.app.call_from_thread(self._show_rtc_result, success, output)

    def _show_rtc_result(self, success: bool, output: str) -> None:

        self.query_one("#sync_rtc_button", Button).disabled = False

        if success:
            self.rtc_status.update("[#5FD68A]RTC synced with local time.[/#5FD68A]")
        else:
            self.rtc_status.update(f"[#E05C5C]Failed: {output.strip()[:200]}[/#E05C5C]")

    # ------------------------------------------------------------------
    # LCD Settings (ControllerState / admin menu)
    # ------------------------------------------------------------------

    def refresh_controller_state(self) -> None:
        self._fetch_controller_state()

    @work(thread=True, exclusive=True, group="router-settings-controller-state")
    def _fetch_controller_state(self) -> None:
        state = system_service.get_controller_state()
        self.app.call_from_thread(self._apply_controller_state, state)

    def _apply_controller_state(self, state) -> None:

        if state is None:
            self.controller_state.update("[#E05C5C]Could not reach the Nano.[/#E05C5C]")
            return

        app_id = state["application_id"]
        type_id = state["type_id"]

        if app_id == 99 and type_id == 99:
            self.controller_state.update("[#5FD68A]Enabled[/#5FD68A]")
        elif app_id == 1 and type_id == 0:
            self.controller_state.update("[#9AA5B1]Disabled[/#9AA5B1]")
        else:
            self.controller_state.update(f"[#E0C341]Custom (ApplicationId={app_id}, TypeId={type_id})[/#E0C341]")

    def _confirm_set_controller_state(self, application_id, type_id, action_label) -> None:

        def handle_result(confirmed: bool):
            if confirmed:
                self.query_one("#enable_admin_menu_button", Button).disabled = True
                self.query_one("#disable_admin_menu_button", Button).disabled = True
                self.lcd_status.update(f"{action_label} - saving and rebooting the Nano...")
                self._apply_controller_state_change(application_id, type_id)

        self.app.push_screen(
            ConfirmDialog(
                f"{action_label} (ApplicationId={application_id}, TypeId={type_id})?\n\n"
                "This reboots the Nano itself - the dashboard will lose "
                "connection briefly and reconnect automatically once it's "
                "back up.",
                title="Reboot Nano?",
                confirm_label=action_label,
            ),
            handle_result,
        )

    @work(thread=True, exclusive=True, group="router-settings-controller-state-change")
    def _apply_controller_state_change(self, application_id, type_id) -> None:

        success = system_service.set_controller_state(application_id, type_id)

        if success:
            system_service.reboot_nano()

        self.app.call_from_thread(self._show_controller_state_result, success)

    def _show_controller_state_result(self, success: bool) -> None:

        self.query_one("#enable_admin_menu_button", Button).disabled = False
        self.query_one("#disable_admin_menu_button", Button).disabled = False

        if success:
            self.lcd_status.update(
                "[#5FD68A]Saved. The Nano is rebooting - this dashboard "
                "will reconnect automatically once it's back up.[/#5FD68A]"
            )
        else:
            self.lcd_status.update(
                "[#E05C5C]Failed to update the setting - the Nano was not rebooted.[/#E05C5C]"
            )
