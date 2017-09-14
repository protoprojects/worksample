# Deployment Notes
## How
Deployment is via [fabric](http://www.fabfile.org)

## Deploying to specific Environments

Running from a sample virtualenv ensures `fab` and necessary support is available

### Production
```sh
fab prod deploy
```

### Continuous Integration
```sh
fab beta deploy
```

### Testing
```sh
fab qa deploy
```

## Tasks Run
The deployment consists of

- git pull of specific branch
- pip install of required python modules
- database sync & migration
- bower & grunt installs for front-end
- static asset management
- restart servers
- provide notification


## Miscellaneous

- encfs:: uses `ENCFS_PASSWORD` from ec2 shell environment
- dbbackup:: executes run_dbbackup.sh *not in repo*
