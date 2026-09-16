"""Geliştirme ortamı için tek seferlik kurulum betiği.

Windows Toast bildirimleri, gönderen sürecin geçerli bir AUMID
(Application User Model ID) ile ilişkilendirilmiş bir Başlat Menüsü
kısayoluna sahip olmasını bekler. Sanal ortamdaki çıplak python.exe'nin
böyle bir kısayolu olmadığı için bildirimler 0x803E0114 hatasıyla
başarısız oluyordu (bkz. Task 5 manuel doğrulama notları).

Bu betik, geliştirme sırasında test edebilmemiz için Başlat Menüsü'ne
AI-Notifier (Dev) adında, AUMID'i ai_notifier.notifications.windows_toast
modülündeki APP_ID sabitiyle eşleşen bir kısayol ekler. PyInstaller ile
paketlenip kurulduğunda (Faz 3) gerçek kurulum bunu otomatik yapacağı
için bu betik yalnızca geliştirme ortamına özeldir, ürün koduna dahil
değildir.

Kullanım:
    python scripts/setup_dev_toast_shortcut.py
"""

import os
import sys

import pythoncom
from win32com.propsys import propsys, pscon
from win32com.shell import shell

from ai_notifier.notifications.windows_toast import APP_ID

SHORTCUT_NAME = "AI-Notifier (Dev).lnk"


def create_shortcut_with_aumid(shortcut_path: str, target: str, aumid: str) -> None:
    shell_link = pythoncom.CoCreateInstance(
        shell.CLSID_ShellLink,
        None,
        pythoncom.CLSCTX_INPROC_SERVER,
        shell.IID_IShellLink,
    )
    shell_link.SetPath(target)

    property_store = shell_link.QueryInterface(propsys.IID_IPropertyStore)
    property_store.SetValue(
        pscon.PKEY_AppUserModel_ID, propsys.PROPVARIANTType(aumid)
    )
    property_store.Commit()

    persist_file = shell_link.QueryInterface(pythoncom.IID_IPersistFile)
    persist_file.Save(shortcut_path, 0)


def main() -> None:
    start_menu_programs = os.path.join(
        os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs"
    )
    shortcut_path = os.path.join(start_menu_programs, SHORTCUT_NAME)
    python_exe = sys.executable

    create_shortcut_with_aumid(shortcut_path, python_exe, APP_ID)
    print(f"Kısayol oluşturuldu: {shortcut_path}")
    print(f"Hedef: {python_exe}")
    print(f"AUMID: {APP_ID}")


if __name__ == "__main__":
    main()
