# %%
import base64
import configparser
import json
import os
import subprocess
import time
import urllib
from datetime import datetime, timedelta, timezone
from os.path import devnull
from pathlib import Path
from typing import Any, List, Optional, Tuple, Union

import boto3
import defusedxml.ElementTree as ET
import inquirer
import typer
from mypy_boto3_cur.literals import AWSRegionType
from mypy_boto3_sts.type_defs import (
    AssumeRoleResponseTypeDef,
    AssumeRoleWithSAMLResponseTypeDef,
)
from rich import print
from seleniumwire import webdriver
from my_utils.aws import session_handler
from my_utils.aws.session_handler import AccessKeyCredential, AssumeRoleConfig
from my_utils.aws.types import EnumActiveAwsRegions

# SAML constants
# The AWS SAML start page that end the authentication process
AWS_SAML_HOMEPAGE_URL = "https://signin.aws.amazon.com/saml"

# Paths for aws config files
AWS_CREDENTIALS_PATH = Path.home() / ".aws" / "credentials"
AWS_PROFILES_PATH = Path.home() / ".aws" / "config"

PROFILE_PATH_CHROME = (
    Path.home() / ".config" / "awscli-saml-login" / "chrome"
)

# The delay in second we wait for awssamlhomepage
AWS_SAML_HOMEPAGE_WAIT_TIMEOUT = 300

CLI_MESSAGE_ONLY_ROLE_BASE = "Selecting only available role: "
SAML_ATTRIBUTE_NAME = "https://aws.amazon.com/SAML/Attributes/Role"

# Identity Pool URL: Right-click AWS icon and "Copy Link" from myapplications.microsoft.com. Update if necessary
IDP_ENTRY_URL = "***"

ERROR_MESSAGE_AWS_ROLES_NOT_FOUND = (
    "Your account is not associated to any role, can't continue."
)
CLI_MESSAGE_PROMT_SELECT_ROLE = (
    "Please choose the role you would like to assume: "
)


def run_x_sever() -> None:
    try:
        subprocess.check_output("pgrep vcxsrv", shell=True)
        is_vcxsrv_running = True
    except subprocess.CalledProcessError:
        is_vcxsrv_running = False
    print("is_vcxsrv_running", is_vcxsrv_running)

    if is_vcxsrv_running:
        return None
    else:
        try:
            subprocess.run(
                f'nohup "/mnt/c/Program Files/VcXsrv/vcxsrv.exe" -multiwindow -clipboard -wgl -ac &> /dev/null',
                check=True,
                shell=True,
            )
        except subprocess.CalledProcessError as e:
            print(f"Error: {e}")
            raise e


def get_chrome_browser() -> webdriver.Chrome:
    options = webdriver.ChromeOptions()

    # Path to the Google Chrome web driver executable

    # Create profile directory for browser if not exist
    if not os.path.isdir(PROFILE_PATH_CHROME):
        os.makedirs(PROFILE_PATH_CHROME, exist_ok=True)

    options.add_argument(f"user-data-dir={str(PROFILE_PATH_CHROME)}")
    driver_path = "/usr/local/bin/chromedriver.exe"

    # Create a new instance of the Chrome driver with the service
    driver = webdriver.Chrome(
        # executable_path=driver_path,
        options=options,
        # service_log_path=devnull,
    )

    return driver


def setup() -> None:
    subprocess.run("./webdriver.sh")


def get_source_roles_from_saml_attributes(saml_assertion: str) -> list[str]:
    """Get source roles from SAML2 attributes."""

    root = ET.fromstring(base64.b64decode(saml_assertion))
    aws_roles: list[str] = []
    for saml2_attribute in root.iter(
        "{urn:oasis:names:tc:SAML:2.0:assertion}Attribute"
    ):
        if saml2_attribute.get("Name") == SAML_ATTRIBUTE_NAME:
            aws_roles += [
                saml2_attribute_value.text
                for saml2_attribute_value in saml2_attribute.iter(
                    "{urn:oasis:names:tc:SAML:2.0:assertion}AttributeValue"
                )
                if saml2_attribute_value.text
            ]

    for aws_role in aws_roles:
        chunks = aws_role.split(",")
        if "saml-provider" in chunks[0]:
            newawsrole = chunks[1] + "," + chunks[0]
            index = aws_roles.index(aws_role)
            aws_roles.insert(index, newawsrole)
            aws_roles.remove(aws_role)

    if len(aws_roles) == 0:
        raise RuntimeError(ERROR_MESSAGE_AWS_ROLES_NOT_FOUND)

    return aws_roles


def request_saml_attributes(  # type: ignore[no-any-unimported]
    browser: Union[webdriver.Chrome, webdriver.Firefox],
) -> str:
    browser.get(IDP_ENTRY_URL)
    request = browser.wait_for_request(
        AWS_SAML_HOMEPAGE_URL, timeout=AWS_SAML_HOMEPAGE_WAIT_TIMEOUT
    )
    saml_assertion = urllib.parse.unquote(str(request.body).split("=")[1])
    browser.quit()

    return saml_assertion


def select_from_prompt(options: list[Any], message: str) -> Any:
    inquiry_name = "default"
    answer = inquirer.prompt(
        [
            inquirer.List(
                inquiry_name,
                message=message,
                choices=options,
            ),
        ],
        theme=inquirer.themes.GreenPassion(),
    )
    selected_source_role: str = answer[inquiry_name]
    print(f'You selected" "{selected_source_role}"')
    return selected_source_role


def select_source_role(aws_roles: List[str]) -> str:
    """CLI dropdown select to select from a list of available source roles."""

    if len(aws_roles) == 1:
        only_source_role: str = aws_roles[0]
        typer.echo(
            typer.style(
                text=only_source_role.split(",")[0],
                fg=typer.colors.GREEN,
                bold=True,
            )
        )
        return only_source_role
    else:
        selected_source_role: str = select_from_prompt(
            options=aws_roles, message=CLI_MESSAGE_PROMT_SELECT_ROLE
        )
        return selected_source_role


def get_saml_session(
    role_arn: str, principal_arn: str, saml_assertion: str
) -> Tuple[boto3.Session, str]:
    """Assume the input role through SAML2 and returns the STS Response payload"""
    # Use the assertion to get an AWS STS token using Assume Role with SAML
    saml_sts_response = (
        session_handler.create_session()
        .client("sts")
        .assume_role_with_saml(
            RoleArn=role_arn,
            PrincipalArn=principal_arn,
            SAMLAssertion=saml_assertion,
        )
    )
    arn = saml_sts_response["AssumedRoleUser"]["Arn"]
    saml_session_name = arn.split("/")[2]

    saml_credentials = saml_sts_response["Credentials"]
    access_key_credential = AccessKeyCredential(
        aws_access_key_id=saml_credentials["AccessKeyId"],
        aws_secret_access_key=saml_credentials["SecretAccessKey"],
        aws_session_token=saml_credentials["SessionToken"],
    )
    session = session_handler.create_session(
        access_key_credential=access_key_credential
    )
    return session, saml_session_name


def get_target_roles_from_s3(session: boto3.Session) -> list[dict]:
    """Fetch a list of available target roles to be assumed from an S3 bucket."""

    s3_client = session.client("s3")
    data = s3_client.get_object(
        Bucket="landing-zone-roles", Key="roles-ng.json"
    )
    contents = data["Body"].read().decode("utf-8")
    target_roles: list[dict] = json.loads(contents)

    return target_roles


def select_target_role(target_roles: list[dict], source_role_arn: str) -> str:
    """CLI dropdown select to select from a list of available target roles."""

    try:
        target: dict[str, Any] = next(
            role
            for role in target_roles
            if role["landing_role"] == source_role_arn
        )
        target_account_roles: list[str] = target["target_roles"]
    except Exception as no_target_role_found:
        raise RuntimeError(
            "Can't find available target roleArn in json file: {error}".format(
                error=no_target_role_found
            )
        ) from no_target_role_found

    if "default" in target:
        default_role: str = target["default"]
        return default_role

    if len(target_account_roles) == 1:
        only_role = target_account_roles[0]
        # click.echo(
        #     message=GREEN_TICK
        #     + CLI_MESSAGE_ONLY_ROLE_BASE
        #     + click.style(
        #         text=only_role.split(",")[0],
        #         fg=CLI_HIGHLIGHT_COLOUR,
        #         bold=True,
        #     )
        # )
        echo(
            f"{typer.style('✔ ', fg='green')}{CLI_MESSAGE_ONLY_ROLE_BASE}{style(only_role.split(',')[0], fg='green', bold=True)}"
        )
        return only_role
    else:
        selected_role: str = select_from_prompt(
            options=target_account_roles, message=CLI_MESSAGE_PROMT_SELECT_ROLE
        )

        return selected_role


def assume_role_from_saml_session(
    selected_target_role_arn: str,
    saml_sts_session: boto3.Session,
    saml_session_name: str,
) -> AssumeRoleResponseTypeDef:
    """Assume the selected target role and returns the STS Response payload as a AssumeRoleResponseTypeDef."""

    assume_role_config = AssumeRoleConfig(
        role_arn=selected_target_role_arn,
        session_name=saml_session_name,
    )

    sts_response = session_handler.get_assume_role_response(
        assume_role_config=assume_role_config,
        session=saml_sts_session,
    )

    return sts_response


def update_aws_profile(
    assume_role_response: AssumeRoleResponseTypeDef,
    profile_name: str,
    region: str,
) -> None:
    """Update and write to AWS CLI config file with the assumed role's
    credentials and configurations.
    """

    credentials_config = configparser.RawConfigParser()
    credentials_config.read(AWS_CREDENTIALS_PATH)

    if not credentials_config.has_section(profile_name):
        credentials_config.add_section(profile_name)

    credentials = assume_role_response["Credentials"]
    credentials_config.set(
        profile_name,
        "aws_access_key_id",
        credentials["AccessKeyId"],
    )
    credentials_config.set(
        profile_name,
        "aws_secret_access_key",
        credentials["SecretAccessKey"],
    )
    credentials_config.set(
        profile_name,
        "aws_session_token",
        credentials["SessionToken"],
    )
    credentials_config.set(
        profile_name,
        "expiration",
        str(credentials["Expiration"].astimezone()),
    )

    # Write the updated config file
    with AWS_CREDENTIALS_PATH.open(mode="w+") as credentials_file:
        credentials_config.write(credentials_file)

    profiles_config = configparser.RawConfigParser()
    profiles_config.read(AWS_PROFILES_PATH)
    profile_section_name = f"profile {profile_name}"
    if not profiles_config.has_section(profile_section_name):
        profiles_config.add_section(profile_section_name)

    profiles_config.set(
        profile_section_name,
        "region",
        region,
    )
    profiles_config.set(
        profile_section_name,
        "output",
        "json",
    )
    with AWS_PROFILES_PATH.open(mode="w+") as profiles_file:
        profiles_config.write(profiles_file)


from typer import echo, style


def login(
    region_name: Optional[EnumActiveAwsRegions] = None,
    #   , target_role: str, region: AWSRegionType
) -> None:
    run_x_sever()
    browser = get_chrome_browser()
    saml_attributes = request_saml_attributes(browser)

    aws_roles = get_source_roles_from_saml_attributes(saml_attributes)
    source_role = select_source_role(aws_roles)

    source_role_arn, principal_arn = source_role.split(",")

    (
        session,
        saml_session_name,
    ) = get_saml_session(source_role_arn, principal_arn, saml_attributes)

    # if not target_role:
    target_roles = get_target_roles_from_s3(session)
    target_role_arn = select_target_role(target_roles, source_role_arn)
    target_role = target_role_arn.split("/")[1]

    if not region_name:
        region_options = [region.value for region in EnumActiveAwsRegions]
        region_name = select_from_prompt(
            options=region_options, message="Please choose the region: "
        )

    assume_role_response = assume_role_from_saml_session(
        selected_target_role_arn=target_role_arn,
        saml_sts_session=session,
        saml_session_name=saml_session_name,
    )
    update_aws_profile(
        assume_role_response=assume_role_response,
        profile_name=target_role,
        region=region_name,
    )

    while True:
        credentials = assume_role_response["Credentials"]
        expires = credentials["Expiration"]
        wait_period = (
            expires - datetime.now(timezone.utc) - timedelta(seconds=30)
        )
        print(
            "😴 Sleeping for {wait_period} before renewing credentials... ".format(
                wait_period=wait_period
            )
        )
        time.sleep(wait_period.seconds)
        print(
            "Renwewing credentials for {target_role}.".format(
                target_role=target_role
            )
        )
        session = session_handler.create_session(
            access_key_credential=AccessKeyCredential(
                aws_access_key_id=credentials["AccessKeyId"],
                aws_secret_access_key=credentials["SecretAccessKey"],
                aws_session_token=credentials["SessionToken"],
            )
        )
        assume_role_response = assume_role_from_saml_session(
            selected_target_role_arn=target_role_arn,
            saml_sts_session=session,
            saml_session_name=saml_session_name,
        )
        update_aws_profile(
            assume_role_response=assume_role_response,
            profile_name=target_role,
            region=region_name,
        )


if __name__ == "__main__":

    login()
