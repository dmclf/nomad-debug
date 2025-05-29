# versions 
`docker pull dmclf/mosek:11.0.21`

`docker pull dmclf/mosek:10.2.17`

# client recommendations

https://docs.mosek.com/latest/pythonfusion/parameters.html#mosek.iparam.cache_license
M.setSolverParam("cacheLicense", "off")
- switch to "off" (default "on")
(otherwise the running process blocks the license during its lifetime, and as we are sharing the license, that will likely cause issues)
 
https://docs.mosek.com/latest/pythonfusion/parameters.html#mosek.iparam.license_wait
M.setSolverParam("licenseWait", "off")
- switch to "on" (default "off")
 
optional:
https://docs.mosek.com/latest/pythonfusion/parameters.html#mosek.iparam.license_pause_time
M.setSolverParam("licensePauseTime", 100)
- feel free to increase

# license file
user is required to acquire a valid license file from mosek for their machine.
test license available through https://www.mosek.com/try/
