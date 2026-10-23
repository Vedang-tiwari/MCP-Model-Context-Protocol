"""Providers package for job discovery."""
from .linkedin import LinkedInProvider
from .indeed import IndeedProvider
from .ats_direct import ATSDirectProvider
from .wellfound import WellfoundProvider
from .naukri import NaukriProvider
from .internshala import InternshalaProvider
from .remoteok import RemoteOKProvider
from .remotive import RemotiveProvider
from .arbeitnow import ArbeitnowProvider

__all__ = [
    "LinkedInProvider",
    "IndeedProvider",
    "ATSDirectProvider",
    "WellfoundProvider",
    "NaukriProvider",
    "InternshalaProvider",
    "RemoteOKProvider",
    "RemotiveProvider",
    "ArbeitnowProvider",
]
