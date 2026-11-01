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
from .workingnomads import WorkingNomadsProvider
from .unstop import UnstopProvider
from .fourdayweek import FourDayWeekProvider
from .ycombinator import YCombinatorProvider
from .simplify import SimplifyJobsProvider
from .devto import DevToProvider
from .crossover import CrossoverProvider
from .cutshort import CutshortProvider
from .foundit import FounditProvider

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
    "WorkingNomadsProvider",
    "UnstopProvider",
    "FourDayWeekProvider",
    "YCombinatorProvider",
    "SimplifyJobsProvider",
    "DevToProvider",
    "CrossoverProvider",
    "CutshortProvider",
    "FounditProvider",
]
