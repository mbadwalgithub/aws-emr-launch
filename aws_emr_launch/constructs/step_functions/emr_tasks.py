# Copyright 2019 Amazon.com, Inc. and its affiliates. All Rights Reserved.
#
# Licensed under the Amazon Software License (the 'License').
# You may not use this file except in compliance with the License.
# A copy of the License is located at
#
#   http://aws.amazon.com/asl/
#
# or in the 'license' file accompanying this file. This file is distributed
# on an 'AS IS' BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied. See the License for the specific language governing
# permissions and limitations under the License.

from typing import Optional, Mapping

from aws_cdk import (
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as sfn_tasks,
    aws_lambda as aws_lambda,
    core
)

from ..lambdas import emr_lambdas
from ..emr_constructs import emr_code


class OverrideClusterConfigs(core.Construct):
    def __init__(self, scope: core.Construct, id: str, *,
                 cluster_config: dict,
                 override_cluster_configs_lambda: Optional[aws_lambda.Function] = None,
                 allowed_cluster_config_overrides: Optional[Mapping[str, str]] = None,
                 output_path: str = '$',
                 result_path: str = '$.ClusterConfig'):
        super().__init__(scope, id)

        override_cluster_configs_lambda = \
            emr_lambdas.OverrideClusterConfigs(self, 'OverrideClusterConfigsLambda').lambda_function \
            if override_cluster_configs_lambda is None \
            else override_cluster_configs_lambda

        self._task = sfn.Task(
            self, 'Override Cluster Configs',
            output_path=output_path,
            result_path=result_path,
            task=sfn_tasks.InvokeFunction(
                override_cluster_configs_lambda,
                payload={
                    'ExecutionInput': sfn.TaskInput.from_context_at('$$.Execution.Input').value,
                    'ClusterConfig': cluster_config,
                    'AllowedClusterConfigOverrides': allowed_cluster_config_overrides
                })
        )

    @property
    def task(self) -> sfn.Task:
        return self._task


class UpdateClusterTags(core.Construct):
    def __init__(self, scope: core.Construct, id: str, *,
                 output_path: str = '$',
                 result_path: str = '$.ClusterConfig'):
        super().__init__(scope, id)

        update_cluster_tags_lambda = emr_lambdas.UpdateClusterTags(
            self, 'UpdateClusterTagsLambda').lambda_function

        self._task = sfn.Task(
            self, 'Update Cluster Tags',
            output_path=output_path,
            result_path=result_path,
            task=sfn_tasks.InvokeFunction(
                update_cluster_tags_lambda,
                payload={
                    'ExecutionInput': sfn.TaskInput.from_context_at('$$.Execution.Input').value,
                    'ClusterConfig': sfn.TaskInput.from_data_at('$.ClusterConfig').value
                })
        )

    @property
    def task(self) -> sfn.Task:
        return self._task


class FailIfClusterRunning(core.Construct):
    def __init__(self, scope: core.Construct, id: str, *, default_fail_if_cluster_running: bool):
        super().__init__(scope, id)

        fail_if_cluster_running_lambda = emr_lambdas.FailIfClusterRunning(
            self, 'FailIfClusterRunningLambda').lambda_function

        self._task = sfn.Task(
            self, 'Fail If Cluster Running',
            output_path='$',
            result_path='$',
            task=sfn_tasks.InvokeFunction(
                fail_if_cluster_running_lambda,
                payload={
                    'ExecutionInput': sfn.TaskInput.from_context_at('$$.Execution.Input').value,
                    'DefaultFailIfClusterRunning': default_fail_if_cluster_running,
                    'ClusterConfig': sfn.TaskInput.from_data_at('$.ClusterConfig').value
                })
        )

    @property
    def task(self) -> sfn.Task:
        return self._task


class CreateCluster(core.Construct):
    def __init__(self, scope: core.Construct, id: str, *,
                 result_path: Optional[str] = None, output_path: Optional[str] = None):
        super().__init__(scope, id)

        run_job_flow_lambda = emr_lambdas.RunJobFlow(self, 'RunJobFlowLambda').lambda_function

        self._task = sfn.Task(
            self, 'Start EMR Cluster',
            output_path=output_path,
            result_path=result_path,
            task=sfn_tasks.RunLambdaTask(
                run_job_flow_lambda,
                integration_pattern=sfn.ServiceIntegrationPattern.WAIT_FOR_TASK_TOKEN,
                payload={
                    'ExecutionInput': sfn.TaskInput.from_context_at('$$.Execution.Input').value,
                    'ClusterConfig': sfn.TaskInput.from_data_at('$.ClusterConfig').value,
                    'TaskToken': sfn.Context.task_token
                })
        )

    @property
    def task(self) -> sfn.Task:
        return self._task


class AddStep(core.Construct):
    def __init__(self, scope: core.Construct, id: str, *,
                 name: str, emr_step: emr_code.EMRStep, cluster_id: str,
                 result_path: Optional[str] = None, output_path: Optional[str] = None):
        super().__init__(scope, id)

        add_job_flow_step_lambda = emr_lambdas.AddJobFlowSteps(self, 'AddJobFlowStepsLambda').lambda_function

        self._task = sfn.Task(
            self, name,
            output_path=output_path,
            result_path=result_path,
            task=sfn_tasks.RunLambdaTask(
                add_job_flow_step_lambda,
                integration_pattern=sfn.ServiceIntegrationPattern.WAIT_FOR_TASK_TOKEN,
                payload={
                    'ExecutionInput': sfn.TaskInput.from_context_at('$$.Execution.Input').value,
                    'ClusterId': cluster_id,
                    'Step': emr_step.resolve(self),
                    'TaskToken': sfn.Context.task_token
                }
            )
        )

    @property
    def task(self) -> sfn.Task:
        return self._task


class TerminateCluster(core.Construct):
    def __init__(self, scope: core.Construct, id: str, *,
                 name: str, cluster_id: str, result_path: Optional[str] = None, output_path: Optional[str] = None):
        super().__init__(scope, id)

        terminate_job_flow_lambda = emr_lambdas.TerminateJobFlow(self, 'TerminateJobFlowLambda').lambda_function

        self._task = sfn.Task(
            self, name,
            output_path=output_path,
            result_path=result_path,
            task=sfn_tasks.RunLambdaTask(
                terminate_job_flow_lambda,
                integration_pattern=sfn.ServiceIntegrationPattern.WAIT_FOR_TASK_TOKEN,
                payload={
                    'ExecutionInput': sfn.TaskInput.from_context_at('$$.Execution.Input').value,
                    'ClusterId': cluster_id,
                    'TaskToken': sfn.Context.task_token
                }
            )
        )

    @property
    def task(self) -> sfn.Task:
        return self._task
