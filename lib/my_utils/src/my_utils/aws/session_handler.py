"""Fucntions and services for creating valid and authenticated boto3 sessions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import partial
from typing import Dict, List, Optional, Union

import boto3
from mypy_boto3_cur.literals import AWSRegionType
from mypy_boto3_sts import STSClient
from mypy_boto3_sts.type_defs import AssumeRoleResponseTypeDef




@dataclass
class AssumeRoleConfig:
    """Parameters needed to assume role using AWS STS."""

    role_arn: str
    session_name: str
    role_name: str = field(init=False)
    policy_arns: Optional[List[Dict[str, str]]] = None
    policy_json_str: Optional[str] = None
    duration_seconds: Optional[int] = 3600

    def __post_init__(self) -> None:
        self.role_name = self.role_arn.split("/")[-1]


@dataclass
class AccessKeyCredential:
    """Parameters needed to authenticate AWS through a access key."""

    aws_access_key_id: str
    aws_secret_access_key: str
    aws_session_token: str


def create_session(
    session: Optional[boto3.Session] = None,
    region_name: Optional[AWSRegionType] = None,
    profile_name: Optional[str] = None,
    access_key_credential: Optional[AccessKeyCredential] = None,
    assume_role_config: Optional[AssumeRoleConfig] = None,
) -> boto3.Session:
    """Create and ensure a valid boto3 session."""

    if access_key_credential is not None:
        return boto3.Session(
            aws_access_key_id=access_key_credential.aws_access_key_id,
            aws_secret_access_key=access_key_credential.aws_secret_access_key,
            aws_session_token=access_key_credential.aws_session_token,
            region_name=region_name,
        )
    if assume_role_config is not None:
        return create_assume_role_session(
            assume_role_config=assume_role_config,
            region_name=region_name,
        )
    if session is not None:
        return session
    if boto3.DEFAULT_SESSION is not None:
        return boto3.DEFAULT_SESSION
    return boto3.Session(region_name=region_name, profile_name=profile_name)


def create_sts_client(
    session: Optional[boto3.Session] = None,
) -> STSClient:
    """Create a S3 Client.

    If no session is passed in, a new session is created to build the client.
    """

    this_session = create_session(session=session)
    sts_client = this_session.client(service_name="sts")
    return sts_client


def get_assume_role_response(
    assume_role_config: AssumeRoleConfig,
    session: Optional[boto3.Session] = None,
) -> AssumeRoleResponseTypeDef:
    """Retrieve assume role response through AWS STS"""

    sts_client = create_sts_client(session)
    assume_role = partial(
        sts_client.assume_role,
        RoleArn=assume_role_config.role_arn,
        RoleSessionName=assume_role_config.session_name,
        DurationSeconds=assume_role_config.duration_seconds,
    )
    if assume_role_config.policy_arns:
        partial(
            assume_role,
            PolicyArns=assume_role_config.policy_arns,
        )

    if assume_role_config.policy_json_str:
        partial(
            assume_role,
            Policy=assume_role_config.policy_json_str,
        )

    assume_role_response = assume_role()
    return assume_role_response


def create_assume_role_session(
    assume_role_config: AssumeRoleConfig,
    session: Optional[boto3.Session] = None,
    region_name: Optional[AWSRegionType] = None,
) -> boto3.Session:
    """Create a assumed role session."""
    assume_role_response = get_assume_role_response(
        assume_role_config,
        session=session,
    )
    credentials = assume_role_response["Credentials"]
    access_key_credentials = AccessKeyCredential(
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
    )
    return create_session(
        access_key_credential=access_key_credentials, region_name=region_name
    )


def get_account_id(
    session: Optional[boto3.Session] = None,
) -> str:
    this_session = create_session(session=session)
    client = this_session.client(service_name="sts")
    return client.get_caller_identity()["Account"]
