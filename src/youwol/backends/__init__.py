"""
This module gathers the router (backends) that are also available in the online environment
(`https://youwol.platform.com` by default).
This ensures consistent behavior for applications that exclusively rely on these backends.
 In local deployments, the backends resolve to their local versions, while in remote setups, they resolve to the
 corresponding remote instances.

"""
