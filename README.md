# BGP_path_hijack
This repo is different from the `https://bitbucket.org/jvimal/bgp/src`, it is an upgradable version for `Mininet 2.3.0`, check it out!
## Envs
- python3
- mininet 2.3.0
## Steps
You should modify the bgp.py in line `147` and `149`, replace the zebra and bgpd's paths to your own!
```
mininet@mininet-vm:$ git https://github.com/spwpun/BGP_Path_Hijack.git
mininet@mininet-vm:$ cd BGP_Path_Hijack/
# replace paths in bgp.py
mininet@mininet-vm:$ sudo python3 bgp.py
# new termial window, connect to S1 router, passwd is "en", type twice with [enter]
mininet@mininet-vm:$ ./connect.sh
bgpd-S1# show bgp all
# new another window, test web service
mininet@mininet-vm:$ ./website.sh
# new another window, start roguing AS
mininet@mininet-vm:$ ./start_rogue.sh
# check the output in `website.sh` windows
mininet@mininet-vm:$ ./stop_rogue.sh
```
