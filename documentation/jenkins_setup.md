# Jenkins Instance Stage-up

## Machine
  Per `https://wiki.jenkins-ci.org/display/JENKINS/Installing+Jenkins+on+Ubuntu`
  
```
wget -q -O - https://jenkins-ci.org/debian/jenkins-ci.org.key | sudo apt-key add -
sudo sh -c 'echo deb http://pkg.jenkins-ci.org/debian binary/ > /etc/apt/sources.list.d/jenkins.list'
sudo apt-get update

apt-get install \
  openjdk-7-jre \  # should be 8
  openjdk-7-jdk \  # should be 8
  jenkins \
  python-pip \
  python-virtualenv
```

 * install jenkins package
 * create `/home/ubuntu/projects` and set permissions
 * install keys in `~/.ssh/` for both `ubuntu` and `jenkins` users for access
 * create config files allowing local ssh and establishing identities in `~/.ssh` folders
 * test keys and add hosts manually using `ssh -T <user>@host`:
   * github.com
   * localhost
 * install other needed packages:
 * install and configure and nginx proxy to allow jenkins access
 * set up git user and email for `ubuntu` and `jenkins`
 
## Jenkins
  * set hostname in `Manage Jenkins` > `config`

  ```
    jenkins.model.JenkinsLocationConfiguration.xml:  <jenkinsUrl>http://ci.sample.com/</jenkinsUrl>
  ```
  * upgrade pre-installed plugins

  ```
  # list installed plugins
  java -jar /root/jenkins-cli.jar -s http://127.0.0.1:8080/ list-plugins

  # list of out-of-date plugins (traps parens for version):
  java -jar /root/jenkins-cli.jar -s http://127.0.0.1:8080/ list-plugins | grep -e ')$' | awk '{ print $1 }

  UPDATE_LIST=$( java -jar /root/jenkins-cli.jar -s http://127.0.0.1:8080/ list-plugins | grep -e ')$' | awk '{ print $1 }' ); 
  if [ ! -z "${UPDATE_LIST}" ]; then 
      echo Updating Jenkins Plugins: ${UPDATE_LIST}; 
      java -jar /root/jenkins-cli.jar -s http://127.0.0.1:8080/ install-plugin ${UPDATE_LIST};
      java -jar /root/jenkins-cli.jar -s http://127.0.0.1:8080/ safe-restart;
  fi

  ```
    
  * Install Github Plugin and configure with SSH access
  * More plugins TBD
  * install ScmSync plugin and configure with `sample/jenkins-config` repo
  * "checkout" + "restore configuration from Github"
  * restart jenkins

  ```
  java -jar /root/jenkins-cli.jar -s http://127.0.0.1:8080/ safe-restart;
  ```  

## ToDos (to take this thing live):
  * Currently access right to github are spread over two users:
    * *samplejenkins*: read-only account for status/monitoring, works for monitoring, has write access for `ScmSync` acces to `jenkins-config` repository.
    * *samplebot*: pull request testers won't work until _contributors_ team has been added with read/write acccess. Contributors includes *samplebot*. Need to minimize accounts and access.
  * Determine to what extent we can replace both github users with read-only deploy keys.
  * We currently use a mixture of hooks and polling to trigger PR builds. Hooks seem preferable, but the github config URLs will include our minimal anti-spider http auth passwords.
  * Determine external accessibility rules, routes, IPs for CI server
  * Deployment user configuration, reconciliation of permissions (`jenkins` vs. `ubuntu`)
  * Database hosts replacement (no more local DB instances)
  * salt slave spot instances with production-like directory structure
  * Establish supported Jenkins version, Java version, plugin versions
  * Experiment with jenkins CLI for package installation and upgrade
  * Bonny doon theme seems to hardcode path to ci.sample (?)

