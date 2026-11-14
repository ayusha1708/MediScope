"""Create the first admin account without a public admin-signup route."""

from getpass import getpass

from mediscope_api.security import public_user
from mediscope_api.services.auth import (
    AuthServiceError,
    EmailAlreadyRegistered,
    create_admin_account,
)


def main() -> None:
    email = input("Admin email: ").strip()
    password = getpass("Admin password (at least 12 characters): ")
    confirmation = getpass("Confirm admin password: ")
    if len(password) < 12:
        raise SystemExit("Admin password must contain at least 12 characters.")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")
    try:
        user = create_admin_account(email, password)
    except EmailAlreadyRegistered as error:
        raise SystemExit(str(error)) from error
    except AuthServiceError as error:
        raise SystemExit(f"Could not create admin account: {error}") from error
    print(f"Admin account created: {public_user(user)['email']}")
    print("No password was displayed or saved in the project files.")


if __name__ == "__main__":
    main()
