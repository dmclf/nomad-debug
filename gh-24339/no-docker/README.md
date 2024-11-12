# non-docker test method
- requires 
  - screen
  - nomad
  - consul
- start: `screen -c .screenrc`

example output (1.9.3)
```
    Deployed
    Task Group  Desired  Placed  Healthy  Unhealthy  Progress Deadline
    cache       20       20      20       0          2024-11-12T17:26:12+08:00
check  :: ALL OK 20 == 20
check  :: ALL OK 20 == 20
check  :: ALL OK 20 == 20
check  :: ALL OK 20 == 20
check  :: ALL OK 20 == 20
check  :: ALL OK 20 == 20
check  :: ALL OK 20 == 20
check  :: ALL OK 20 == 20
check  :: ALL OK 20 == 20
check  :: ALL OK 20 == 20
check  :: ALL OK 20 == 20
check  :: MISMATCH 20 != 2
check  :: MISMATCH 20 != 2
check  :: MISMATCH 20 != 1
check  :: MISMATCH 20 != 0
check  :: MISMATCH 20 != 0
check  :: MISMATCH 20 != 0
```
