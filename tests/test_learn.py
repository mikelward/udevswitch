import unittest

from support import Case, FakeMonitor, make_edid, read, uswitch

DP1, HDMI1 = 0x0F, 0x11


class LearnTest(Case):
    def setUp(self):
        super().setUp()
        self.edid = make_edid(serial="AAA")
        self.sysfs.add_monitor("card0-DP-1", self.edid, bus=4)
        self.sysfs.add_monitor("card0-eDP-1", make_edid(serial="PANEL"), bus=1)
        self.monitor = self.runner.add(("--bus", "4"), FakeMonitor(DP1), DP1)

    def add_switch(self):
        """The switch's USB 3 hub pair and a mouse behind it, plus a built-in trackpad."""
        self.sysfs.add_usb("3-2", "05e3", "0610", hub=True, speed="480", name="USB2.1 Hub")
        self.sysfs.add_usb("4-2", "05e3", "0620", hub=True, speed="5000", name="USB3.1 Hub")
        self.sysfs.add_usb("3-2.1", "046d", "c52b", speed="12", name="Receiver")
        self.sysfs.add_usb("1-1", "06cb", "00bd", speed="12", name="Touchpad")

    def press(self, away_at=1.0, back_at=3.0, take_monitor=True):
        """Press the switch away and back; the other machine runs uswitch."""

        def away():
            for port in ("3-2", "4-2", "3-2.1"):
                self.sysfs.remove_usb(port)
            if take_monitor:
                self.monitor.current = HDMI1

        def back():
            self.sysfs.add_usb("3-2", "05e3", "0610", hub=True, speed="480", name="USB2.1 Hub")
            self.sysfs.add_usb("4-2", "05e3", "0620", hub=True, speed="5000", name="USB3.1 Hub")
            self.sysfs.add_usb("3-2.1", "046d", "c52b", speed="12", name="Receiver")

        self.clock.at(away_at, away)
        self.clock.at(back_at, back)

    def learned(self):
        return uswitch.load_config(self.path(uswitch.CONFIG))

    def rules(self):
        return read(self.path(uswitch.UDEV_RULE))

    def test_setup_a_learns_the_switchs_usb2_hub(self):
        self.add_switch()
        self.press()
        self.answers = ["home", "a", ""]
        self.assertEqual(uswitch.learn(self.ctx), 0)
        config = self.learned()
        self.assertEqual(config.desks["home"].usb, uswitch.UsbTrigger("05e3", "0610"))
        self.assertEqual([(m.desk, m.serial, m.input) for m in config.monitors], [("home", "AAA", DP1)])
        self.assertIn('ATTR{idVendor}=="05e3", ATTR{idProduct}=="0610", RUN+="/usr/bin/systemctl --no-block start uswitch.service"', self.rules())
        self.assertEqual(self.monitor.current, DP1)
        self.assertIn("switched back from another input", self.out.getvalue())

    def test_setup_a_pins_the_port_when_a_dock_has_the_same_hub_chip(self):
        self.add_switch()
        self.sysfs.add_usb("1-4", "05e3", "0610", hub=True, speed="480", name="Dock hub")
        self.press()
        self.answers = ["home", "a", ""]
        self.assertEqual(uswitch.learn(self.ctx), 0)
        self.assertEqual(self.learned().desks["home"].usb, uswitch.UsbTrigger("05e3", "0610", "", "3-2"))
        self.assertIn('KERNEL=="3-2"', self.rules())

    def test_setup_a_brings_the_monitors_back_when_reads_stop_answering(self):
        self.monitor.inactive_reads = False
        self.add_switch()
        self.press()
        self.answers = ["home", "a", ""]
        self.assertEqual(uswitch.learn(self.ctx), 0)
        self.assertEqual(self.monitor.current, DP1)
        self.assertIn("switched back from another input", self.out.getvalue())
        self.assertLess(self.clock.now(), self.ctx.timing.learn_away)

    def test_setup_a_asks_when_several_devices_qualify(self):
        self.sysfs.add_usb("3-2", "046d", "c52b", speed="12", name="Receiver")
        self.sysfs.add_usb("3-3", "04d9", "0169", speed="12", name="Keyboard")

        def away():
            self.sysfs.remove_usb("3-2")
            self.sysfs.remove_usb("3-3")
            self.monitor.current = HDMI1

        def back():
            self.sysfs.add_usb("3-2", "046d", "c52b", speed="12", name="Receiver")
            self.sysfs.add_usb("3-3", "04d9", "0169", speed="12", name="Keyboard")

        self.clock.at(1.0, away)
        self.clock.at(3.0, back)
        self.answers = ["home", "a", "", "2"]
        self.assertEqual(uswitch.learn(self.ctx), 0)
        self.assertEqual(self.learned().desks["home"].usb, uswitch.UsbTrigger("04d9", "0169"))

    def test_setup_a_gives_up_when_nothing_leaves(self):
        self.add_switch()
        self.answers = ["home", "a", ""]
        with self.assertRaises(uswitch.UswitchError) as e:
            uswitch.learn(self.ctx)
        self.assertIn("no USB device left", str(e.exception))
        self.assertIsNone(self.learned())

    def test_usb_option_skips_the_presses(self):
        self.add_switch()
        self.clock.at(1.0, lambda: setattr(self.monitor, "current", HDMI1))  # its buttons
        self.answers = [""]
        self.assertEqual(uswitch.learn(self.ctx, desk_name="home", usb_spec="05E3:0610"), 0)
        self.assertEqual(self.learned().desks["home"].usb, uswitch.UsbTrigger("05e3", "0610"))

    def test_usb_option_needs_the_device_connected(self):
        self.answers = [""]
        with self.assertRaises(uswitch.UswitchError) as e:
            uswitch.learn(self.ctx, desk_name="home", usb_spec="05e3:0610")
        self.assertIn("is connected", str(e.exception))

    def test_usb_option_rejects_a_malformed_id(self):
        with self.assertRaises(uswitch.UswitchError):
            uswitch.learn(self.ctx, desk_name="home", usb_spec="05e3")

    def test_setup_b_learns_a_desk_without_a_switch(self):
        self.clock.at(1.0, lambda: setattr(self.monitor, "current", HDMI1))  # its buttons
        self.answers = ["work", "b", ""]
        self.assertEqual(uswitch.learn(self.ctx), 0)
        config = self.learned()
        self.assertIsNone(config.desks["work"].usb)
        self.assertNotIn("ACTION", self.rules())
        self.assertEqual(self.monitor.current, DP1)

    def test_a_monitor_that_never_left_is_reported_untested(self):
        self.answers = ["work", "b", ""]
        self.assertEqual(uswitch.learn(self.ctx), 0)
        self.assertIn("switching from another input is untested", self.out.getvalue())
        self.assertGreaterEqual(self.clock.now(), self.ctx.timing.learn_away)

    def test_a_monitor_that_doesnt_come_back_fails(self):
        self.monitor.ignore_writes = 99
        self.clock.at(1.0, lambda: setattr(self.monitor, "current", HDMI1))
        self.answers = ["work", "b", ""]
        self.assertEqual(uswitch.learn(self.ctx), 1)
        self.assertIn("didn't come back", self.err.getvalue())

    def test_learning_a_second_desk_keeps_the_first(self):
        home = self.config({"home": uswitch.UsbTrigger("05e3", "0610")}, [("home", make_edid(serial="HOME"), DP1)])
        self.write_config(home)
        self.answers = ["", "b", ""]  # the default name is a new desk's
        self.assertEqual(uswitch.learn(self.ctx), 0)
        config = self.learned()
        self.assertEqual(sorted(config.desks), ["desk1", "home"])
        self.assertIn('ATTR{idProduct}=="0610"', self.rules())

    def test_relearning_defaults_to_the_monitors_desk(self):
        self.write_config(self.config({"work": None}, [("work", self.edid, HDMI1)]))
        self.answers = ["", "b", ""]
        self.assertEqual(uswitch.learn(self.ctx), 0)
        self.assertEqual([(m.desk, m.input) for m in self.learned().monitors], [("work", DP1)])

    def test_no_monitor_answering_ddc_is_an_error(self):
        self.runner.monitors.clear()
        with self.assertRaises(uswitch.UswitchError) as e:
            uswitch.learn(self.ctx)
        self.assertIn("no connected monitor answers DDC/CI", str(e.exception))

    def test_identical_monitors_without_serials_are_learned_once(self):
        twin = make_edid(serial="")
        self.sysfs.remove_monitor("card0-DP-1")
        self.sysfs.add_monitor("card0-DP-1", twin, bus=4)
        self.sysfs.add_monitor("card0-DP-2", twin, bus=5)
        self.runner.add(("--bus", "5"), FakeMonitor(DP1), DP1)
        self.clock.at(1.0, lambda: setattr(self.monitor, "current", HDMI1))
        self.answers = ["work", "b", ""]
        self.assertEqual(uswitch.learn(self.ctx), 0)
        self.assertEqual(len(self.learned().monitors), 1)
        self.assertIn("identical to another connected monitor", self.err.getvalue())

    def test_the_laptop_panel_is_never_part_of_a_desk(self):
        self.answers = ["work", "b", ""]
        uswitch.learn(self.ctx)
        self.assertEqual([m.serial for m in self.learned().monitors], ["AAA"])


if __name__ == "__main__":
    unittest.main()
