#!/usr/bin/python
DOCUMENTATION = """
---
module: eda_activations
short_description: Manage activations in EDA Controller
version_added: '1.0'
author: Your Name
description:
  - This module allows you to create activations in EDA Controller for a given project.
options:
  controller_url:
    description:
      - The URL of the EDA Controller API.
    required: true
  project_name:
    description:
      - The name of the project in EDA Controller.
    required: true
  controller_user:
    description:
      - The username for authentication with the EDA Controller API.
    required: true
  controller_password:
    description:
      - The password for authentication with the EDA Controller API.
    required: true
    no_log: true
  restart_policy:
    description:
      - The restart policy for the activations. Default is "always".
    required: false
    default: "always"
  enabled:
    description:
      - Whether the activations should be enabled. Default is true.
    required: false
    default: true
  decision_env:
    description:
      - The name of the decision environment in EDA Controller.
    required: true
  activations:
    description:
      - A list of activation objects containing the following parameters:
        - name: The name of the activation.
        - rulebook: The name of the rulebook associated with the activation.
        - extra_vars: (Optional) Additional variables for the activation.
    required: true
"""

from ansible.module_utils.basic import AnsibleModule
import requests


def get_project_id(controller_url, controller_user, controller_password, project_name):
    url = f"{controller_url}/api/eda/v1/projects/?name={project_name.replace(' ', '+')}"
    response = requests.get(url, auth=(controller_user, controller_password), verify=False)
    if response.status_code in (200, 201):
        results = response.json().get('results', [])
        if results:
            return int(results[0].get('id'))
    return None


def get_decision_environment_id(controller_url, controller_user, controller_password, decision_env):
    url = f"{controller_url}/api/eda/v1/decision-environments/?name={decision_env.replace(' ', '+')}"
    response = requests.get(url, auth=(controller_user, controller_password), verify=False)
    if response.status_code in (200, 201):
        results = response.json().get('results', [])
        if results:
            return int(results[0].get('id'))
    return None


def create_activations(module):
    # Extract input parameters from the module object
    controller_url = module.params['controller_url']
    controller_user = module.params['controller_user']
    controller_password = module.params['controller_password']
    activations = module.params['activations']

    rulebook_list = []
    extra_vars_list = []

    # Create activations for given project
    url = f"{controller_url}/api/eda/v1/activations/"
    response_list = []

    for activation in activations:
        project_name = activation['project_name']
        project_id = get_project_id(controller_url, controller_user, controller_password, project_name)
        if not project_id:
            module.fail_json(msg=f"Project '{project_name}' not found.")

        # Retrieve rulebooks
        url = f"{controller_url}/api/eda/v1/rulebooks/?project_id={project_id}"
        response = requests.get(url, auth=(controller_user, controller_password), verify=False)
        if response.status_code in (200, 201):
            rulebooks = response.json().get('results', [])
            for rulebook in rulebooks:
                if rulebook['name'] == activation['rulebook']:
                    rulebook_list.append({'name': activation['name'], 'id': int(rulebook['id'])})
                    break

        # Create extra vars for activations
        if 'extra_vars' in activation and activation['extra_vars']:
            url = f"{controller_url}/api/eda/v1/extra-vars/"
            body = {"extra_var": activation['extra_vars']}
            response = requests.post(url, auth=(controller_user, controller_password),
                                     json=body, verify=False)
            if response.status_code in (200, 201):
                extra_vars_list.append({'name': activation['name'], 'var_id': int(response.json().get('id'))})

        denv_id = get_decision_environment_id(controller_url, controller_user, controller_password, activation['decision_env'])
        if not denv_id:
            module.fail_json(msg=f"Decision environment '{activation['decision_env']}' not found.")

        name = activation['name']
        rulebook_id = None
        extra_var_id = None

        for rulebook in rulebook_list:
            if rulebook['name'] == name:
                rulebook_id = rulebook['id']
                break

        for extra_vars in extra_vars_list:
            if extra_vars['name'] == name:
                extra_var_id = extra_vars['var_id']
                break

        activation_item = {
            'name': name,
            'project_id': project_id,
            'decision_environment_id': denv_id,
            'rulebook_id': rulebook_id,
            'restart_policy': activation.get('restart_policy', 'always'),
            'is_enabled': activation.get('enabled', True)
        }

        if extra_var_id is not None:
            activation_item['extra_var_id'] = extra_var_id

        response = requests.post(url, auth=(controller_user, controller_password),
                                 json=activation_item, verify=False)
        if response.status_code in (200, 201):
            response_list.append(response.json())

    module.exit_json(changed=True, activations=response_list)


def main():
    module_args = dict(
        controller_url=dict(type='str', required=True),
        controller_user=dict(type='str', required=True),
        controller_password=dict(type='str', required=True, no_log=True),
        activations=dict(type='list', required=True, elements='dict', options=dict(
            project_name=dict(type='str', required=True),
            decision_env=dict(type='str', required=True),
            name=dict(type='str', required=True),
            rulebook=dict(type='str', required=True),
            extra_vars=dict(type='str', default=''),
            restart_policy=dict(type='str', default='always'),
            enabled=dict(type='bool', default=True)
            ),
        ),
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=False
    )

    try:
        create_activations(module)
    except Exception as e:
        module.fail_json(msg=str(e))


if __name__ == '__main__':
    main()
