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
from .hirist import HiristProvider
from .devfolio import DevfolioProvider
from .aijobnet import AIJobNetProvider
from .beepai import BeepAIProvider
from .sprout import SproutProvider
from .icrunchdata import ICrunchDataProvider
from .mljobsinfo import MLJobsInfoProvider
from .aijobsai import AIJobsAIProvider

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
    "HiristProvider",
    "DevfolioProvider",
    "AIJobNetProvider",
    "BeepAIProvider",
    "SproutProvider",
    "ICrunchDataProvider",
    "MLJobsInfoProvider",
    "AIJobsAIProvider",
]
