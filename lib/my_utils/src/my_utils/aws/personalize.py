import time
from functools import partial
from typing import Callable, Dict, List, Literal, Optional, Sequence, TypedDict, Union

from my_utils.aws.session_handler import create_session
from my_utils.log import logger
from mypy_boto3_personalize.client import PersonalizeClient
from mypy_boto3_personalize.literals import (
    ImportModeType,
    PaginatorName,
    TrainingModeType,
)
from mypy_boto3_personalize.type_defs import SolutionConfigTypeDef, TagTypeDef
from prefect import task

AWSPersonalizeDatasetType = Literal["Interactions", "Items", "Users"]
PersonalizeResources = Literal[
    "schema",
    "dataset-group",
    "dataset",
    "solution",
    "filter",
    "solution-version",
    "dataset-import-job",
    "batch-inference-job",
]


class ResoureDesciption(TypedDict):
    func: Callable
    arg: Dict


class ResourePaginatorInfo(TypedDict):
    paginator: PaginatorName
    response_info_key: str
    arn_key: str


RESOURCE_PAGINATORS: Dict[PersonalizeResources, ResourePaginatorInfo] = {
    "schema": {
        "paginator": "list_schemas",
        "response_info_key": "schemas",
        "arn_key": "schemaArn",
    },
    "dataset-group": {
        "paginator": "list_dataset_groups",
        "response_info_key": "datasetGroups",
        "arn_key": "datasetGroupArn",
    },
    "dataset": {
        "paginator": "list_datasets",
        "response_info_key": "datasets",
        "arn_key": "datasetArn",
    },
    "solution": {
        "paginator": "list_solutions",
        "response_info_key": "solutions",
        "arn_key": "solutionArn",
    },
    "solution-version": {
        "paginator": "list_solution_versions",
        "response_info_key": "solutionVersions",
        "arn_key": "solutionVersionArn",
    },
    "filter": {
        "paginator": "list_filters",
        "response_info_key": "Filters",
        "arn_key": "filterArn",
    },
}


def get_personalize_client() -> PersonalizeClient:
    session = create_session()
    client = session.client("personalize")
    return client


def get_exsiting_resouce_arn(
    resource_name: str,
    resource_type: PersonalizeResources,
    personalize: PersonalizeClient,
    **paginate_arg: Optional[str],
) -> str:
    paginator_info = RESOURCE_PAGINATORS[resource_type]
    paginator = personalize.get_paginator(paginator_info["paginator"])
    resource_arn = ""
    found_resource = False
    for resource_group in paginator.paginate(**paginate_arg):
        for resource in resource_group[paginator_info["response_info_key"]]:
            if resource_type == "solution-version":
                resource_name_ref = resource[paginator_info["arn_key"]].split(
                    "/"
                )[-1]
            else:
                resource_name_ref = resource["name"]
            if resource_name_ref == resource_name:
                resource_arn = resource[paginator_info["arn_key"]]
                found_resource = True
                break
        if found_resource == True:
            break
    return resource_arn


@task(
    name="get_dataset_group",
    task_run_name="get_dataset_group: {dataset_group_name}",
)
def get_dataset_group(
    dataset_group_name: str,
    personalize: PersonalizeClient,
    tags: Optional[Sequence[TagTypeDef]] = None,
) -> str:
    try:
        response = personalize.create_dataset_group(name=dataset_group_name)
        dataset_group_arn = response["datasetGroupArn"]
        if tags is not None:
            personalize.tag_resource(resourceArn=dataset_group_arn, tags=tags)
        logger.info(f"New Dataset Group: {dataset_group_arn}")
    except personalize.exceptions.ResourceAlreadyExistsException:
        dataset_group_arn = get_exsiting_resouce_arn(
            resource_name=dataset_group_name,
            resource_type="dataset-group",
            personalize=personalize,
        )
        logger.info(f"Existing Dataset Group: {dataset_group_arn}")
    return dataset_group_arn


def prepare_schema(
    schema_name: str,
    personalize: PersonalizeClient,
    schema_path: Optional[str] = None,
) -> str:
    with open(schema_path) as f:
        schema = f.read()
    if schema_path is not None:
        schema_arn = personalize.create_schema(
            name=schema_name,
            schema=schema,
        )["schemaArn"]
        logger.info(f"New Schema: {schema_arn}")
    else:
        schema_arn = get_exsiting_resouce_arn(
            resource_name=schema_name,
            resource_type="schema",
            personalize=personalize,
        )
        logger.info(f"Existing Schema: {schema_arn}")
    return schema_arn


def get_dataset(
    dataset_group_arn: str,
    dataset_type: AWSPersonalizeDatasetType,
    schema_path: Optional[str] = None,
    tags: Optional[Sequence[TagTypeDef]] = None,
) -> str:
    dataset_group_name = dataset_group_arn.split("/")[-1]
    dataset_name = f"{dataset_group_name}_{dataset_type}"
    personalize = get_personalize_client()

    if schema_path is not None:
        schema_arn = prepare_schema(
            schema_name=dataset_name,
            personalize=personalize,
            schema_path=schema_path,
        )
        response = personalize.create_dataset(
            name=dataset_name,
            schemaArn=schema_arn,
            datasetGroupArn=dataset_group_arn,
            datasetType=dataset_type,
        )
        dataset_arn = response["datasetArn"]
        if tags is not None:
            personalize.tag_resource(resourceArn=dataset_arn, tags=tags)
        logger.info(f"New Dataset: {dataset_arn}")
    else:
        dataset_arn = get_exsiting_resouce_arn(
            resource_name=dataset_name,
            resource_type="dataset",
            personalize=personalize,
            datasetGroupArn=dataset_group_arn,
        )
        logger.info(f"Existing Dataset: {dataset_arn}")
    return dataset_arn


@task(
    name="prepare_solution",
    task_run_name="prepare_solution: {solution_name}",
)
def prepare_solution_version(
    dataset_group_arn: str,
    solution_name: str,
    solution_version_name: str,
    training_mode: Optional[TrainingModeType] = None,
    recipe_arn: Optional[str] = None,
    tags: Optional[Sequence[TagTypeDef]] = None,
) -> str:
    solution_arn = get_solution(
        solution_name=solution_name,
        dataset_group_arn=dataset_group_arn,
        recipe_arn=recipe_arn,
        tags=tags,
    )
    if recipe_arn is not None:
        check_active(resource_arn=solution_arn, resource_type="solution")
    solution_version_arn = get_solution_version(
        solution_version_name=solution_version_name,
        solution_arn=solution_arn,
        training_mode=training_mode,
        tags=tags,
    )
    return solution_version_arn


def create_import_job(
    data_path: str,
    dataset_arn: str,
    import_mode: ImportModeType,
    role_arn: str,
) -> None:
    personalize = get_personalize_client()
    dataset_name = "_".join(dataset_arn.split("/")[-2:])
    file_name = data_path.split("/")[-1]
    response = personalize.create_dataset_import_job(
        jobName=f"{dataset_name}_{file_name}",
        datasetArn=dataset_arn,
        dataSource={"dataLocation": data_path},
        roleArn=role_arn,
        importMode=import_mode,
    )
    logger.info(
        f"{dataset_arn} Import Job Creation Starts, Import Mode: {import_mode}"
    )
    import_job_arn = response["datasetImportJobArn"]
    check_active(import_job_arn, resource_type="dataset-import-job")


def check_active(
    resource_arn: str,
    resource_type: PersonalizeResources,
    interval: int = 5,
    max_duration: int = 60,
) -> bool:
    personalize = get_personalize_client()
    resource_types_collection: Dict[str, ResoureDesciption] = {
        "dataset": {
            "func": personalize.describe_dataset,
            "arg": {"datasetArn": resource_arn},
        },
        "dataset-import-job": {
            "func": personalize.describe_dataset_import_job,
            "arg": {"datasetImportJobArn": resource_arn},
        },
        "solution-version": {
            "func": personalize.describe_solution_version,
            "arg": {"solutionVersionArn": resource_arn},
        },
        "batch-inference-job": {
            "func": personalize.describe_batch_inference_job,
            "arg": {"batchInferenceJobArn": resource_arn},
        },
        "filter": {
            "func": personalize.describe_filter,
            "arg": {"filterArn": resource_arn},
        },
        "solution": {
            "func": personalize.describe_solution,
            "arg": {"solutionArn": resource_arn},
        },
    }

    max_time = time.time() + max_duration
    logger.info(f"Monitoring Resource Status: {resource_arn}")
    target_resource = resource_types_collection[resource_type]
    while time.time() < max_time:
        response = target_resource["func"](**target_resource["arg"])
        for values in response.values():
            if "status" in values.keys():
                status = values["status"]
                break
            else:
                logger.error(f"No Status for Resource: {resource_arn}")
                return False

        if status == "ACTIVE":
            logger.info(f"Resource Active: {resource_arn}")
            return True
        elif status == "CREATE FAILED":
            logger.error(f"Creation Failed: {resource_arn}")
            return False
        else:
            time.sleep(interval)
    logger.warning(
        f"Monitoring Timeout: {resource_arn}, Last Status: {status}"
    )
    return False


def get_solution(
    solution_name: str,
    dataset_group_arn: str,
    recipe_arn: Optional[str] = None,
    tags: Optional[Sequence[TagTypeDef]] = None,
    soltion_config: Optional[SolutionConfigTypeDef] = None,
) -> str:
    personalize = get_personalize_client()
    if recipe_arn is not None:
        create_solution = partial(
            personalize.create_solution,
            name=solution_name,
            datasetGroupArn=dataset_group_arn,
            recipeArn=recipe_arn,
            tags=tags,
        )
        if soltion_config is not None:
            partial(create_solution, solutionConfig=soltion_config)
        if tags is not None:
            partial(create_solution, tags=tags)
        response = create_solution()
        solution_arn = response["solutionArn"]
        logger.info(f"New Solution: {solution_arn}")
    else:
        solution_arn = get_exsiting_resouce_arn(
            resource_name=solution_name,
            resource_type="solution",
            personalize=personalize,
            datasetGroupArn=dataset_group_arn,
        )
        logger.info(f"Existing Solution: {solution_arn}")
    return solution_arn


def get_solution_version(
    solution_version_name: str,
    solution_arn: str,
    training_mode: Optional[TrainingModeType] = None,
    tags: Optional[Sequence[TagTypeDef]] = None,
) -> str:
    personalize = get_personalize_client()
    if training_mode is not None:
        create_solution_version = partial(
            personalize.create_solution_version,
            name=solution_version_name,
            solutionArn=solution_arn,
            trainingMode=training_mode,
        )
        # check_active(resource_arn=)
        if tags is not None:
            partial(create_solution_version, tags=tags)
        response = create_solution_version()
        solution_version_arn = response["solutionVersionArn"]
        logger.info(f"New Solution Version: {solution_version_arn}")
    else:
        solution_version_arn = get_exsiting_resouce_arn(
            resource_name=solution_version_name,
            resource_type="solution-version",
            personalize=personalize,
            solutionArn=solution_arn,
        )
        logger.info(f"Existing Solution Version: {solution_version_arn}")
    return solution_version_arn


@task(
    name="get_filter",
    task_run_name="get_filter: {filter_name}",
)
def get_filter(
    filter_name: str,
    dataset_group_arn: str,
    filter_expression: Optional[
        str
    ] = None,  # https://docs.aws.amazon.com/personalize/latest/dg/filter-expressions.html
    tags: Optional[Sequence[TagTypeDef]] = None,
) -> str:
    """Input name of existing filter with new filter expression will NOT update the filter"""
    personalize = get_personalize_client()
    if filter_expression is not None:
        response = personalize.create_filter(
            name=filter_name,
            datasetGroupArn=dataset_group_arn,
            filterExpression=filter_expression,
        )
        filter_arn = response["filterArn"]
        if tags is not None:
            personalize.tag_resource(resourceArn=filter_arn, tags=tags)
        logger.info(f"New Filter: {filter_arn}")
    else:
        filter_arn = get_exsiting_resouce_arn(
            resource_name=filter_name,
            resource_type="filter",
            personalize=personalize,
            datasetGroupArn=dataset_group_arn,
        )
        logger.info(f"Existing Filter: {filter_arn}")
    return filter_arn


@task(
    name="batch_inference",
    task_run_name="batch_inference: {job_name}",
)
def create_batch_inference_job(
    job_name: str,
    solution_version_arn: str,
    s3_input_path: str,
    s3_output_path: str,
    role_arn: str ,
    filter_arn: Optional[str] = None,
    tags: Optional[Sequence[TagTypeDef]] = None,
    
) -> str:
    personalize = get_personalize_client()
    create_batch_inference_job = partial(
        personalize.create_batch_inference_job,
        solutionVersionArn=solution_version_arn,
        jobName=job_name,
        roleArn=role_arn,
        jobInput={"s3DataSource": {"path": s3_input_path}},
        jobOutput={"s3DataDestination": {"path": s3_output_path}},
    )
    if filter_arn is not None:
        partial(create_batch_inference_job, filterArn=filter_arn)
    if tags is not None:
        partial(create_batch_inference_job, tags=tags)
    response = create_batch_inference_job()
    return response["batchInferenceJobArn"]

