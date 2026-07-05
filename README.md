# Discord Account Generator
# https://venumzmail.xyz 

https://github.com/nkdevofficial/Discord-Account-Generator

a discord account creator that uses venumzmail for temporary emails and nopecha for captcha solving and mullvad auto rotate 

## how to use

1. install python 3.9 or higher, only works for 3.9 or higher
2. install requirements: pip install -r requirements.txt
3. put your api keys in input/config.json
4. run the script: python gen.py
5. enter how many accounts you want (0 for infinite)

## api keys needed

- venumzmail api key from https://venumzmail.xyz
- nopecha api key from https://nopecha.com

## proxy setup (optional)

add proxies to input/proxies.txt
format: socks5://user:pass@ip:port or http://user:pass@ip:port

## where accounts are saved

output/valid.txt - working accounts (email:password:token)
output/locked.txt - locked accounts
output/invalid.txt - invalid accounts
output/unverified.txt - email not verified

## requirements

- python 3.8+
- brave browser (or chrome)

## Disclamier

This tool is for educational purposes only. The developer is not responsible for any misuse, violations of Discord’s Terms of Service, or potential bans. Use at your own risk.

## contact
discord: nkdev.official or nkdevv_alt
