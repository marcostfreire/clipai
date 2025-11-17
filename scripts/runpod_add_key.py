import os

KEY = (
    "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC/xozkvNC2LJx93fgz27pbmEQBW1gDb2W8SqaZUgRLgsnrPvD3mFk5NEzLe"
    "RrJq1qJ1G6G7DKFPzuuKEBadaG0SS57H8aIYS5Qr6iZiSxB3O1FwOOjLmlVuZrU3N/0UB8qlMn7QmbjaBX6/2vEFabfsUh/xtGKaPwa7tLpDoDSzcY5kalauvKOms/HA8YCtIJkI325kwkxehmNYcV83nnDhRTUmYInQinjs1KB8B4Szc9N0+RbhmR1n7aMqC/PIQwPPaP/YUu/LZZk3CERLdghAsdlmgehwaFkG3XXFDjus0XyGTB3thGIJ60ix++zMld1quMGFpCpBbqStpcmu5S9 RunPod-Key-Go"
)


def ensure_key_present() -> None:
    """Append the CLI public key to ~/.ssh/authorized_keys if needed."""

    auth_dir = os.path.expanduser("~/.ssh")
    auth_file = os.path.join(auth_dir, "authorized_keys")
    os.makedirs(auth_dir, exist_ok=True)

    existing = ""
    if os.path.exists(auth_file):
        with open(auth_file, "r", encoding="utf-8") as handle:
            existing = handle.read()

    if KEY in existing:
        print("Key already registered; nothing to do.")
        return

    with open(auth_file, "a", encoding="utf-8") as handle:
        if existing and not existing.endswith("\n"):
            handle.write("\n")
        handle.write(KEY)
        handle.write("\n")

    print("Key appended to authorized_keys.")


if __name__ == "__main__":
    ensure_key_present()
