import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from core.database import connect_database
from core.runtime import harden_private_runtime_storage


class RuntimePermissionTests(unittest.TestCase):
    def test_private_runtime_state_is_owner_only(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            database = root / "wreckscanner.sqlite3"
            wal = Path(f"{database}-wal")
            shm = Path(f"{database}-shm")
            private = root / "prywatne_zdjecia"
            database.write_bytes(b"db")
            wal.write_bytes(b"wal")
            shm.write_bytes(b"shm")
            private.mkdir(mode=0o755)
            previous_umask = os.umask(0o022)
            try:
                harden_private_runtime_storage(database_path=database, private_photos_dir=private)
                probe = root / "probe"
                probe.write_bytes(b"private")
            finally:
                os.umask(previous_umask)

            self.assertEqual(private.stat().st_mode & 0o777, 0o700)
            self.assertEqual(database.stat().st_mode & 0o777, 0o600)
            self.assertEqual(wal.stat().st_mode & 0o777, 0o600)
            self.assertEqual(shm.stat().st_mode & 0o777, 0o600)
            self.assertEqual(probe.stat().st_mode & 0o777, 0o600)

    def test_private_storage_symlink_is_rejected(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "target"
            target.mkdir()
            private_link = root / "private-link"
            private_link.symlink_to(target, target_is_directory=True)
            previous_umask = os.umask(0o022)
            try:
                with self.assertRaisesRegex(RuntimeError, "dowiązaniem symbolicznym"):
                    harden_private_runtime_storage(
                        database_path=root / "wreckscanner.sqlite3",
                        private_photos_dir=private_link,
                    )
            finally:
                os.umask(previous_umask)

    def test_database_connection_hardens_database_before_wal_setup(self):
        with TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "state.sqlite3"
            previous_umask = os.umask(0o022)
            try:
                connection = connect_database(database)
                connection.execute("CREATE TABLE private_data (value TEXT)")
                connection.commit()
                modes = {
                    path.name: path.stat().st_mode & 0o777
                    for path in database.parent.iterdir()
                    if path.name.startswith(database.name)
                }
                connection.close()
            finally:
                os.umask(previous_umask)

            self.assertEqual(modes[database.name], 0o600)
            self.assertTrue(all(mode == 0o600 for mode in modes.values()))


if __name__ == "__main__":
    unittest.main()
