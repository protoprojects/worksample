# Using nginx against localhost without grunt/gulp serve

While `gulp` and `grunt serve` are a convenient system for front-end debugging, it's hopelessly inefficient when you need an unchanging back-end for local debugging, or where HTTPS-based debugging is necessary. A local instance of nginx can more accurately mirror production and prevent massive battery and resource drain, especially while working disconnected.

## Installing nginx
on OSX, (assuming you have homebrew and xcode installed alread - you need these in order to get a development environemnt working), you can just:

```
brew install nginx
which nginx
# if this does not return a path to the executable, create a symbolic link:
# sudo brew link --overwrite nginx
```

On unix, your package management software may vary but something like `sudo yum install nginx` or `sudo apt-get nginx` should do the trick.

## Paths you'll need
in order to debug consumer and advisor portal, you'll need to point nginx at the build output directories for both systems. Optionally, it's possible (albeit unecessary for almost all cases) to provide mapping for your local development directories. For the purposes of this document, we'll create three aliases, mirroring production:

```
consumer.sample.dev
advisor.sample.dev
api.sample.dev
```

we'll point these to the paths where you've performed your checkouts and builds of local front ends. In my case, this is:

```
/Users/andycarra/rksh/sample                      # we'll call this <sample PATH>
/Users/andycarra/rksh/sample-advisor_portal/dist  # we'll call this <ADVISOR PATH>
/Users/andycarra/rksh/consumer-portal/dist        # we'll call this <CONSUMER PATH>
```

For the following instructions to work, you'll need to remember to run `gulp build` in the `consumer-portal` root and `grunt-build` in the `sample-advisor_portal` root in order to update the static assets to be served.

## local DNS aliases
in order to allow local DNS resolution, we'll update the local domain hosts file. For MacOS and most unixes, this will be located in `/etc/hosts`. In some uncommon cases, you need to ensure that local file-based domain name resolution trumps remote lookup, but this is unlikely in most modern linux and BSD variants. Use your favorite text editor to add/update the localhost lines in the `hosts` file (you'll need root/admin access):

```
127.0.0.1       localhost api.sample.dev consumer.sample.dev advisor.sample.dev
::1             localhost api.sample.dev consumer.sample.dev advisor.sample.dev
```

`127.0.0.1` is the IPv4 localhost alias and `::1` is the IPv6 localhost alias (you can skip the second one if you somehow have a unix variant that doesn't support IPv6 in this day and age)

You can test these aliases by pinging each hostname:

```
ping advisor.sample.dev
```

should yield:

```
PING localhost (127.0.0.1): 56 data bytes
64 bytes from 127.0.0.1: icmp_seq=0 ttl=64 time=0.045 ms
...
```
&etc.


## local SSL Certficate Generation

To keep things simple, we'll generate one certificate for all three servers. Add other entries under `alt_name` as necessary. The Common Name (`CN`) entry must be repeated as a Subject Alternative Name (SAN), because the standard directs clients to ignore the Common Name once _any_ SANs are present.

In a temp directory, create a certificate signing request config (into a file named `openssl.conf`):

```
cat > openssl.cnf <<-EOF
  [req]
  distinguished_name = req_distinguished_name
  x509_extensions = v3_req
  prompt = no
  [req_distinguished_name]
  CN = api.sample.dev
  [v3_req]
  keyUsage = keyEncipherment, dataEncipherment
  extendedKeyUsage = serverAuth
  subjectAltName = @alt_names
  [alt_names]
  DNS.1 = api.sample.dev
  DNS.2 = advisor.sample.dev
  DNS.3 = consumer.sample.dev
EOF
```

Then use the signing request to generate a key and cert:

```
openssl req \
  -new \
  -newkey rsa:2048 \
  -sha1 \
  -days 3650 \
  -nodes \
  -x509 \
  -keyout localssl.key \
  -out localssl.crt \
  -config openssl.cnf
```

finally, remove the temp request config

```
rm openssl.cnf
```

You can check the certificate using the following command:

```
openssl x509 -in ./localssl.crt -text -noout
```

See [this reference](https://www.sslshopper.com/article-most-common-openssl-commands.html) for advanced OpenSSL command reference.

This will leave nothing in your temp dir except `localssl.crt` (the certificate) and `localssl.key` (the key) you'll move these to the certificate locations of `SERVER CERT LOCATION` and `SERVER KEY LOCATION` in the steps below (you'll probably need to sudo).



### For OSX
Before moving the certificate, you'll want to tell your OS to trust it:

```
open /Applications/Utilities/Keychain\ Access.app localssl.crt
```
Make sure _Keychain:_ *login* is selected and click _Add_.
The "Keychain Access" tool will open, and you'll be able to find an *api.sample.dev* certificate in the UI (under *All Items*).

Open this, provide password if necessary, and under "When using this certificate" select "Always Trust"

```
sudo mkdir /usr/local/etc/nginx/ssl/
sudo mv localssl.crt /usr/local/etc/nginx/ssl/
sudo mv localssl.key /usr/local/etc/nginx/ssl/
```

### For other unixes

for most linuxes:

```
sudo mv localssl.crt /etc/ssl/certs/
sudo mv localssl.key /etc/ssl/private/

```

or this (if you don't want to pollute your central cert store):

```
sudo mkdir /etc/nginx/ssl/
sudo mv localssl.crt /etc/nginx/ssl/
sudo mv localssl.key /etc/nginx/ssl/
```



## nginx configuration
Now, we stick it all together. Serve the local paths from a local nginx installation, using the directories we located above.

on OSX, the nginx configuration is located in `/usr/local/etc/nginx`. Under ubuntu and other linuxes, you can install nginx via your package manager, and you'll find the default configuration stored in `/etc/nginx`

To start nginx automatically, use:

```
sudo cp -v /usr/local/opt/nginx/*.plist /Library/LaunchDaemons/
sudo chown root:wheel /Library/LaunchDaemons/homebrew.mxcl.nginx.plist
```

See [here](http://launchd.info/) for an OSX launchd tutorial.

### OSX-specific
In order to make an OSX nginx installation more-or-less compatibile with linux nginx installations, we'll make and include the standard `sites-enabled` and `sites-available` directories under the root config directory:

```
 # in the nginx configuration directory:
 mkdir sites-enabled
 mkdir sites-available
```

then update `NGINX_CONFG_DIR/nginx.conf` to include the contents of `sites-enabled` (must be placed inside the `http {}` block of the nginx configuration):

```
include sites-enabled/*;
```

### Add a Configuration for Each Domain Name

Using the <SERVER CERT> and <SERVER KEY> files you generated above, create a file in the `sites-available` directory (use the `Config Name` in the table below) for for each host you want to expose:

```
  # SWAP THIS BLOCK IN FOR LIVE DEBUGGING (1/2)
  # upstream <BACKEND NAME> {
  #  server 127.0.0.1:<DEV SERVICE PORT>;
  # }

  # redirect from 80 to 443
  server {
    server_name <SERVER NAME>;
    rewrite ^(.*) https://<SERVER NAME>$1 permanent;
  }

  server {
    listen               443;
    ssl                  on;
    ssl_certificate      <SERVER CERT LOCATION>;  # /usr/local/etc/nginx/ssl/localssl.crt
    ssl_certificate_key  <SERVER KEY LOCATINON>;  # /usr/local/etc/nginx/ssl/localssl.key
    keepalive_timeout    70;
    server_name <SERVER NAME>;
    location / {
      # SWAP THIS IN FOR LIVE DEBUGGING (2/2)
      # proxy_pass  http://<BACKEND NAME>;
      root <PATH>;
      index index.html;
    }
  }
```

Varying `<BACKEND NAME>`, `<SERVER NAME>` and `<DEV SERVICE PORT>` according to the following table, and make sure to match the correct server cert/key:

 file name       | SERVER NAME         | DEV PORT      | BACKEND NAME   | PATH               |
| --------------- | ------------------- | ------------- | -------------- | ------------------ |
| api-server      | api.sample.dev      | 8000          | api-back       | sample PATH        |
| advisor-portal  | advisor.sample.dev  | 9002          | advisor-back   | ADVISOR PATH       |
| consumer-portal | consumer.sample.dev | 3000          | consumer-back  | CONSUMER PATH      |

### Enable the Configurations

Create symbolic links to `sites-available` configuration files to `sites-enabled` to activate configurations.

```
  ln -s <NGINX CONFIG ROOT>/sites-available/<CONFIG NAME> <NGINX CONFIG ROOT>/sites-enabled/<CONFIG NAME>
```
on the mac, this would be:

```
sudo ln -s /usr/local/etc/nginx/sites-available/api-server /usr/local/etc/nginx/sites-enabled/api-server
sudo ln -s /usr/local/etc/nginx/sites-available/advisor-portal /usr/local/etc/nginx/sites-enabled/advisor-portal
sudo ln -s /usr/local/etc/nginx/sites-available/consumer-portal /usr/local/etc/nginx/sites-enabled/consumer-portal
```

Then test the config using

```
nginx -t  # may need sudo
```

before restarting


## Django Settings

Modify your `website/settings/dev/dev.py` in accordance with the `Consumer Portal` and `SSL` references in the latest `website/settings/dev/dev.py.example`. Then, re-start Django.


## Finally

navigate to each address in your browser of choice:

```
https://advisor.sample.dev
https://consumer.sample.dev
```

and accept the new SSL certificates permanently into the browser trust store.
