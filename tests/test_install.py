import os
import unittest

from support import PROGRAM, Case, FakeMonitor, make_edid, read, uswitch

INSTALLED = [uswitch.PROGRAM, uswitch.UNIT, uswitch.POLKIT_RULE, uswitch.MODULES_LOAD]


class InstallTest(Case):
    def learned(self, wake=True):
        config = self.config({"home": uswitch.UsbTrigger("05e3", "0610")}, [("home", make_edid(serial="AAA"), 0x0F)], wake)
        self.write_config(config)

    def files(self):
        found = []
        for base, _, names in os.walk(self.root):
            found += [os.path.relpath(os.path.join(base, n), self.root) for n in names]
        return sorted(found)

    def test_installs_every_file_and_enables_wake(self):
        self.learned()
        self.assertEqual(uswitch.install(self.ctx), 0)
        self.assertEqual(self.files(), sorted(INSTALLED + [uswitch.CONFIG, uswitch.UDEV_RULE]))
        self.assertTrue(os.access(self.path(uswitch.PROGRAM), os.X_OK))
        self.assertEqual(read(self.path(uswitch.PROGRAM)), read(PROGRAM))
        self.assertIn(["systemctl", "--root", self.root, "enable", "uswitch.service"], self.runner.calls)
        self.assertIn('ATTR{idProduct}=="0610"', read(self.path(uswitch.UDEV_RULE)))

    def test_wake_off_disables_the_boot_and_resume_hook(self):
        self.learned(wake=False)
        self.assertEqual(uswitch.install(self.ctx), 0)
        self.assertIn(["systemctl", "--root", self.root, "disable", "uswitch.service"], self.runner.calls)

    def test_is_idempotent(self):
        self.learned()
        uswitch.install(self.ctx)
        first = {f: read(self.path(f)) for f in self.files()}
        self.assertEqual(uswitch.install(self.ctx), 0)
        self.assertEqual({f: read(self.path(f)) for f in self.files()}, first)

    def test_refuses_without_ddcutil_naming_the_package(self):
        self.runner.missing.add("ddcutil")
        with self.assertRaises(uswitch.UswitchError) as e:
            uswitch.install(self.ctx)
        self.assertIn("install the ddcutil package", str(e.exception))
        self.assertEqual(self.files(), [])

    def test_learns_when_nothing_is_learned_yet(self):
        self.sysfs.add_monitor("card0-DP-1", make_edid(serial="AAA"), bus=4)
        monitor = self.runner.add(("--bus", "4"), FakeMonitor(0x0F), 0x0F)
        self.clock.at(1.0, lambda: setattr(monitor, "current", 0x11))
        self.answers = ["work", "b", ""]
        self.assertEqual(uswitch.install(self.ctx), 0)
        self.assertIn("running `uswitch learn`", self.out.getvalue())
        self.assertIn(uswitch.CONFIG, self.files())

    def test_live_install_loads_i2c_dev_and_reloads(self):
        self.learned()
        live = []
        self.ctx.run = lambda argv, timeout: live.append(argv) or uswitch.Result(0, "", "")
        # A live root writes the real system; point every path into the test root instead.
        self.ctx.path = lambda rel: os.path.join(self.root, rel)
        self.ctx.root = "/"
        self.assertEqual(uswitch.install(self.ctx), 0)
        self.assertEqual(
            live,
            [
                ["modprobe", "i2c-dev"],
                ["systemctl", "daemon-reload"],
                ["udevadm", "control", "--reload"],
                ["systemctl", "enable", "uswitch.service"],
            ],
        )

    def test_a_failing_command_is_reported(self):
        self.learned()
        self.runner.failing["systemctl"] = "Failed to enable unit"
        with self.assertRaises(uswitch.UswitchError) as e:
            uswitch.install(self.ctx)
        self.assertIn("Failed to enable unit", str(e.exception))


class UninstallTest(Case):
    def setUp(self):
        super().setUp()
        self.write_config(self.config({"home": None}, [("home", make_edid(serial="AAA"), 0x0F)]))
        uswitch.install(self.ctx)

    def remaining(self):
        found = []
        for base, _, names in os.walk(self.root):
            found += [os.path.relpath(os.path.join(base, n), self.root) for n in names]
        return found

    def test_removes_everything_but_the_configuration(self):
        self.assertEqual(uswitch.uninstall(self.ctx), 0)
        self.assertEqual(self.remaining(), [uswitch.CONFIG])
        self.assertIn(["systemctl", "--root", self.root, "disable", "uswitch.service"], self.runner.calls)
        self.assertIn("uninstall --purge", self.out.getvalue())

    def test_purge_removes_the_configuration_too(self):
        self.assertEqual(uswitch.uninstall(self.ctx, purge=True), 0)
        self.assertEqual(self.remaining(), [])

    def test_is_idempotent(self):
        uswitch.uninstall(self.ctx, purge=True)
        self.runner.calls.clear()
        self.assertEqual(uswitch.uninstall(self.ctx, purge=True), 0)
        self.assertEqual(self.runner.commands("systemctl"), [])
        self.assertIn("Removed nothing", self.out.getvalue())


if __name__ == "__main__":
    unittest.main()
