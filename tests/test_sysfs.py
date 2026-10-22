import unittest

from support import Case, make_edid, uswitch


class EdidTest(unittest.TestCase):
    def test_parses_manufacturer_model_and_serial(self):
        edid = uswitch.parse_edid(make_edid("DEL", "DELL U2723QE", "ABC1234"))
        self.assertEqual((edid.mfg, edid.model, edid.serial), ("DEL", "DELL U2723QE", "ABC1234"))
        self.assertEqual(len(edid.hex), 256)

    def test_missing_serial_is_empty(self):
        edid = uswitch.parse_edid(make_edid(serial=""))
        self.assertEqual(edid.serial, "")
        self.assertEqual(edid.model, "DELL U2723QE")

    def test_rejects_what_isnt_an_edid(self):
        self.assertIsNone(uswitch.parse_edid(b""))
        self.assertIsNone(uswitch.parse_edid(bytes(128)))


class ConnectedMonitorsTest(Case):
    def test_finds_connected_external_monitors_with_their_bus(self):
        self.sysfs.add_monitor("card0-DP-1", make_edid(serial="AAA"), bus=4)
        self.sysfs.add_monitor("card0-HDMI-A-1", make_edid(serial="BBB"))
        found = uswitch.connected_monitors(self.sysfs.root)
        self.assertEqual([(c.name, c.edid.serial, c.bus) for c in found], [("card0-DP-1", "AAA", 4), ("card0-HDMI-A-1", "BBB", None)])
        self.assertEqual(found[0].ddcutil_args(), ["--bus", "4"])
        self.assertEqual(found[1].ddcutil_args(), ["--edid", found[1].edid.hex])

    def test_skips_disconnected_internal_and_edidless_connectors(self):
        self.sysfs.add_monitor("card0-DP-2", make_edid(serial="AAA"), status="disconnected")
        self.sysfs.add_monitor("card0-eDP-1", make_edid(serial="PANEL"))
        self.sysfs.add_monitor("card0-DP-3", b"")
        self.assertEqual(uswitch.connected_monitors(self.sysfs.root), [])

    def test_no_drm_at_all_is_no_monitors(self):
        self.assertEqual(uswitch.connected_monitors(self.tmp + "/nowhere"), [])


class UsbDevicesTest(Case):
    def test_reads_devices_and_skips_root_hubs_and_interfaces(self):
        self.sysfs.add_usb("3-2", "05E3", "0610", serial="S1", hub=True, name="USB2.1 Hub")
        self.sysfs.add_usb("usb3", "1d6b", "0002", hub=True)
        self.sysfs.add_usb("3-2:1.0", "05e3", "0610")
        devices = uswitch.usb_devices(self.sysfs.root)
        self.assertEqual(list(devices), ["3-2"])
        d = devices["3-2"]
        self.assertEqual((d.vendor, d.product, d.serial, d.hub, d.speed, d.depth), ("05e3", "0610", "S1", True, 480.0, 1))

    def test_a_re_enumerated_device_is_equal_but_a_new_generation(self):
        self.sysfs.add_usb("3-2", hub=True)
        before = uswitch.usb_devices(self.sysfs.root)
        self.sysfs.remove_usb("3-2")
        self.sysfs.add_usb("3-2", hub=True)
        after = uswitch.usb_devices(self.sysfs.root)
        self.assertEqual(before, after)
        trigger = uswitch.UsbTrigger("1234", "5678")
        self.assertNotEqual(trigger.generation(before), trigger.generation(after))
        self.assertEqual(trigger.generation({}), frozenset())

    def test_depth_counts_hubs_between_device_and_root(self):
        self.sysfs.add_usb("1-4.2.1")
        self.assertEqual(uswitch.usb_devices(self.sysfs.root)["1-4.2.1"].depth, 3)


class TriggerTest(Case):
    def device(self, port, **kw):
        self.sysfs.add_usb(port, **kw)
        return uswitch.usb_devices(self.sysfs.root)[port]

    def test_unique_identity_needs_no_port(self):
        d = self.device("3-2", serial="S1", hub=True)
        self.device("1-1", vendor="aaaa", product="bbbb")
        t = uswitch.trigger_for(d, uswitch.usb_devices(self.sysfs.root))
        self.assertEqual(t, uswitch.UsbTrigger("1234", "5678", "S1", ""))

    def test_a_shared_identity_pins_the_port(self):
        d = self.device("3-2", hub=True)
        self.device("1-4", hub=True)  # the same generic hub chip in a dock
        t = uswitch.trigger_for(d, uswitch.usb_devices(self.sysfs.root))
        self.assertEqual(t, uswitch.UsbTrigger("1234", "5678", "", "3-2"))

    def test_an_unsafe_serial_is_dropped_and_the_port_pinned(self):
        for serial in ('ab"c', "a*b", "a?b", "a[b]", "a|b", "a\\b"):
            with self.subTest(serial=serial):
                d = uswitch.UsbDevice("3-2", "1234", "5678", serial, "", True, 480)
                t = uswitch.trigger_for(d, {"3-2": d})
                self.assertEqual(t, uswitch.UsbTrigger("1234", "5678", "", "3-2"))

    def test_matching_honors_serial_and_port(self):
        d = uswitch.UsbDevice("3-2", "1234", "5678", "S1", "", True, 480)
        self.assertTrue(uswitch.UsbTrigger("1234", "5678").matches(d))
        self.assertTrue(uswitch.UsbTrigger("1234", "5678", "S1", "3-2").matches(d))
        self.assertFalse(uswitch.UsbTrigger("1234", "5678", "S2").matches(d))
        self.assertFalse(uswitch.UsbTrigger("1234", "5678", port="3-3").matches(d))
        self.assertFalse(uswitch.UsbTrigger("1234", "9999").matches(d))

    def test_candidates_prefer_shallow_then_hub_then_usb2_half(self):
        devices = [
            uswitch.UsbDevice("2-2", "1234", "0620", "", "", True, 5000),  # SuperSpeed half
            uswitch.UsbDevice("1-2", "1234", "0610", "", "", True, 480),  # USB 2 half
            uswitch.UsbDevice("1-2.1", "046d", "c52b", "", "", False, 12),  # the mouse behind it
        ]
        self.assertEqual([d.port for d in uswitch.trigger_candidates(devices)], ["1-2"])

    def test_candidates_without_a_hub_fall_back_to_the_devices(self):
        devices = [
            uswitch.UsbDevice("1-2", "046d", "c52b", "", "", False, 12),
            uswitch.UsbDevice("1-3", "04d9", "0169", "", "", False, 12),
        ]
        self.assertEqual([d.port for d in uswitch.trigger_candidates(devices)], ["1-2", "1-3"])
        self.assertEqual(uswitch.trigger_candidates([]), [])


if __name__ == "__main__":
    unittest.main()
