# -*- mode: ruby -*-


#=======================================|SETTINGS|============================
PROJECT_NAME = 'sample'
DJANGO_HOST_PORT = 8000
DJANGO_GUEST_PORT = 8000
#=============================================================================


VAGRANTFILE_API_VERSION = "2"
Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|

  config.vm.box = "precise32"
  config.vm.box_url = "http://files.vagrantup.com/precise32.box"

  config.vm.network "forwarded_port", guest: DJANGO_GUEST_PORT, host: DJANGO_HOST_PORT

  config.vm.synced_folder "./", "/home/vagrant/#{PROJECT_NAME}"

  ## For masterless, mount your salt file root
  config.vm.synced_folder "salt/salt/", "/srv/salt/"
  config.vm.synced_folder "salt/pillar/", "/srv/pillar/"

  config.vm.provision :salt do |salt|

    salt.minion_config = "salt/minion.conf"
    salt.run_highstate = true
    salt.verbose = true

  end
end
