#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys
import shutil
import qrcode

from jinja2 import Template

def get_wg():
  wg = shutil.which('wg')
  return wg

def getargs():
  parser = argparse.ArgumentParser(description='Generate wireguard client config                                                                                                                                                             .')
  parser.add_argument('client')
  parser.add_argument('ip')
  args = parser.parse_args()
  return args

def generate_keys(client):
  os.umask(0o77)
  client_dir = 'clients'
  server_dir = 'server'
  wg = get_wg()

  if not os.path.isdir(client_dir):
    os.makedirs(client_dir)

  for name in ('{0}.conf'.format(client),'{0}.png'.format(client)):
    if os.path.isfile(os.path.join(client_dir,name)):
      print('[!] Files already exist! Exiting.')
      sys.exit(1)

  privatekey = subprocess.check_output([
      wg,
      'genkey'
    ])

  publickey = subprocess.check_output([
      wg,
      'pubkey'
    ], input=privatekey)

  preshared = None
  if os.path.isfile(os.path.join(server_dir, 'preshared')):
    preshared = open(os.path.join(server_dir, 'preshared'), 'r').read().strip()

  return privatekey, publickey, preshared

def generate_config(privatekey, preshared, ip):
  server_dir = 'server'
  publickey = open(os.path.join(server_dir, 'publickey'), 'r').read()
  template = Template("""[Interface]
Address = {{ ip }}/24
PrivateKey = {{ privatekey }}
DNS = 192.168.1.1

[Peer]
PublicKey = {{ publickey }}
{% if preshared %}PresharedKey = {{ preshared }}{% endif %}
AllowedIPs = 0.0.0.0/0, ::/0
Endpoint = slurpgeit.nl:51337

""")

  config = template.render(
    privatekey=privatekey.decode('utf-8').strip(),
    publickey=publickey.strip(),
    preshared=preshared.strip(),
    ip=ip
  )

  return config

def write_config(config, client):
  client_dir = 'clients'

  with open(os.path.join(client_dir,'{0}.conf'.format(client)),'w') as f:
    print('[+] Writing config.')
    f.write(config)

  print('[+] Writing QR code.')
  img = qrcode.make(config)
  img.save(os.path.join(client_dir,'{0}.png'.format(client)))

def generate_server_config(publickey, preshared, client, ip):
  template = Template("""
# {{ client }}
[Peer]
PublicKey = {{ publickey }}
AllowedIPs = {{ ip }}/32
PersistentKeepalive = 25
{% if preshared %}PresharedKey = {{ preshared }}{% endif %}

""")

  config = template.render(
    publickey=publickey.decode('utf-8').strip(),
    preshared=preshared.strip(),
    client=client,
    ip=ip
  )

  print('[+] Add to server peer config:')
  print(config)

def main():
  args = getargs()
  privatekey, publickey, preshared = generate_keys(args.client)
  config = generate_config(privatekey, preshared, args.ip)
  write_config(config, args.client)
  generate_server_config(publickey, preshared, args.client, args.ip)

if __name__ == '__main__':
  main()
