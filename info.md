## Pods
resulting_harlequin_gamefowl
ID qh3hpqrnck8ila

## SSH
Connect to your pod using SSH. (No support for SCP & SFTP)
ssh -i ~/.ssh/id_ed25519_runpod qh3hpqrnck8ila-644113f7@ssh.runpod.io

## SSH over exposed TCP
Connect to your pod using SSH over a direct TCP connection. (Supports SCP & SFTP)
ssh root@213.173.109.76 -p 14760 -i ~/.ssh/id_ed25519

## Direct TCP Ports
Connect to your pod using direct TCP connections to exposed ports.

213.173.109.76:14760 → :22

## Container
wphkv67a0p

### Start Command

bash -c ' apt update; apt install -y wget; mkdir -p /workspace; DEBIAN_FRONTEND=noninteractive apt-get install openssh-server -y; mkdir -p ~/.ssh; chmod 700 ~/.ssh; echo "$PUBLIC_KEY" >> ~/.ssh/authorized_keys; chmod 700 ~/.ssh/authorized_keys; service ssh start; wget https://bootstrap.pypa.io/get-pip.py -O get-pip.py; python3 get-pip.py; rm get-pip.py; pip3 install -U --no-cache-dir jupyterlab jupyterlab_widgets ipykernel ipywidgets; jupyter lab --allow-root --no-browser --port=8888 --ip=* --ServerApp.terminado_settings="{\"shell_command\":[\"/bin/bash\"]}" --ServerApp.token=$JUPYTER_PASSWORD --ServerApp.allow_origin=* --FileContentsManager.preferred_dir=/workspace; sleep infinity '

# Stripe CLI

Use the command line to manage your Stripe resources in a sandbox.

You can use the Stripe CLI to build, test, and manage your integration from the command line. With the Stripe CLI, you can perform common tasks, like calling an API, testing a webhooks integration, and creating an application. See the [Stripe CLI reference](https://docs.stripe.com/cli.md).

[Install the Stripe CLI](https://docs.stripe.com/stripe-cli/install.md): Install the Stripe CLI on macOS, Windows, or Linux.

[Use the Stripe CLI](https://docs.stripe.com/stripe-cli/use-cli.md): Learn how to use the Stripe CLI to build, test, and manage your integration from the command line.

[Enable autocompletion](https://docs.stripe.com/stripe-cli/autocomplete.md): Let the Stripe CLI automatically complete your commands.

[Stripe CLI keys and permissions](https://docs.stripe.com/stripe-cli/keys.md): Learn about Stripe CLI keys, where they’re stored, and how to find their permissions.

[Upgrade the Stripe CLI](https://docs.stripe.com/stripe-cli/upgrade.md): Keep your Stripe CLI up to date to access new features, improvements, and security updates.