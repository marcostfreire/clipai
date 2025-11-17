SSH
Connect to your pod using SSH. (No support for SCP & SFTP)

 
ssh qh3hpqrnck8ila-644113f7@ssh.runpod.io -i ~/.ssh/id_ed25519_runpod
SSH over exposed TCP
Connect to your pod using SSH over a direct TCP connection. (Supports SCP & SFTP)

 
ssh root@213.173.109.76 -p 14760 -i ~/.ssh/id_ed25519_runpod