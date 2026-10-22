"""Platform Registry managing built-in providers, custom declarative platforms,
and drop-in Python plugin providers.
"""
import json
import logging
import importlib.util
from pathlib import Path
from typing import Dict, List, Any, Optional

from discovery.base import BaseJobProvider
from core.models import CustomPlatformConfig, PlatformType
from core.config import CONFIG_DIR, ROOT_DIR
from discovery.providers import (
    LinkedInProvider,
    IndeedProvider,
    ATSDirectProvider,
    WellfoundProvider,
    NaukriProvider,
    InternshalaProvider
)
from discovery.providers.custom_dynamic import CustomPlatformProvider

logger = logging.getLogger(__name__)


class PlatformRegistry:
    def __init__(self, custom_platforms_path: Optional[Path] = None, plugins_dir: Optional[Path] = None):
        self.custom_platforms_path = custom_platforms_path or (CONFIG_DIR / "custom_platforms.json")
        self.plugins_dir = plugins_dir or (ROOT_DIR / "discovery" / "plugins")
        self.plugins_dir.mkdir(parents=True, exist_ok=True)

        self.providers: Dict[str, BaseJobProvider] = {}
        self.custom_configs: Dict[str, CustomPlatformConfig] = {}

        self._init_defaults()
        self.load_all()

    def _init_defaults(self):
        """Initializes default custom platforms file if it does not exist."""
        if not self.custom_platforms_path.exists():
            default_platforms = [
                {
                    "name": "remoteok",
                    "display_name": "RemoteOK",
                    "platform_type": "rss",
                    "enabled": True,
                    "url_template": "https://remoteok.com/remote-jobs.rss",
                    "max_items_per_cycle": 20
                },
                {
                    "name": "weworkremotely",
                    "display_name": "WeWorkRemotely",
                    "platform_type": "rss",
                    "enabled": True,
                    "url_template": "https://weworkremotely.com/categories/remote-programming-jobs.rss",
                    "max_items_per_cycle": 20
                },
                {
                    "name": "jobicy",
                    "display_name": "Jobicy API",
                    "platform_type": "json_api",
                    "enabled": True,
                    "url_template": "https://jobicy.com/api/v2/remote-jobs?count=20&tag={role}",
                    "field_mappings": {
                        "items": "jobs",
                        "title": "jobTitle",
                        "company": "companyName",
                        "url": "url",
                        "location": "jobGeo",
                        "description": "jobExcerpt"
                    },
                    "max_items_per_cycle": 20
                }
            ]
            with open(self.custom_platforms_path, "w", encoding="utf-8") as f:
                json.dump(default_platforms, f, indent=2)

    def load_all(self):
        """Loads built-in providers, custom configured platforms, and Python plugins."""
        self.providers.clear()
        self.custom_configs.clear()

        # 1. Register Core Built-In Providers
        self.providers["ats_direct"] = ATSDirectProvider()
        self.providers["linkedin"] = LinkedInProvider()
        self.providers["indeed"] = IndeedProvider()
        self.providers["wellfound"] = WellfoundProvider()
        self.providers["naukri"] = NaukriProvider()
        self.providers["internshala"] = InternshalaProvider()

        # 2. Load Custom Platforms from JSON
        if self.custom_platforms_path.exists():
            try:
                with open(self.custom_platforms_path, "r", encoding="utf-8") as f:
                    configs_raw = json.load(f)
                    for item in configs_raw:
                        cfg = CustomPlatformConfig(**item)
                        self.custom_configs[cfg.name] = cfg
                        if cfg.enabled:
                            self.providers[cfg.name] = CustomPlatformProvider(cfg)
            except Exception as e:
                logger.error(f"Failed to load custom platforms from {self.custom_platforms_path}: {e}")

        # 3. Load Python Plugins from discovery/plugins/*.py
        self._load_plugins()

        logger.info(f"PlatformRegistry loaded {len(self.providers)} active platforms.")

    def _load_plugins(self):
        """Scans plugins_dir and dynamically registers any BaseJobProvider subclass."""
        for file_path in self.plugins_dir.glob("*.py"):
            if file_path.name.startswith("__"):
                continue
            try:
                module_name = f"discovery.plugins.{file_path.stem}"
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    for attr_name in dir(mod):
                        attr = getattr(mod, attr_name)
                        if isinstance(attr, type) and issubclass(attr, BaseJobProvider) and attr != BaseJobProvider:
                            instance = attr()
                            self.providers[instance.name] = instance
                            logger.info(f"Loaded platform plugin: {instance.name} from {file_path.name}")
            except Exception as e:
                logger.error(f"Error loading plugin {file_path.name}: {e}")

    def add_custom_platform(self, config: CustomPlatformConfig) -> bool:
        """Registers a new custom platform and persists it to JSON."""
        self.custom_configs[config.name] = config
        if config.enabled:
            self.providers[config.name] = CustomPlatformProvider(config)
        self._save_custom_configs()
        logger.info(f"Successfully added platform '{config.name}' ({config.platform_type.value})")
        return True

    def remove_custom_platform(self, name: str) -> bool:
        """Removes a custom platform from active registry and JSON."""
        if name in self.custom_configs:
            del self.custom_configs[name]
            self.providers.pop(name, None)
            self._save_custom_configs()
            logger.info(f"Removed custom platform '{name}'")
            return True
        return False

    def toggle_platform(self, name: str, enabled: bool) -> bool:
        """Enables or disables a platform."""
        if name in self.custom_configs:
            self.custom_configs[name].enabled = enabled
            if enabled:
                self.providers[name] = CustomPlatformProvider(self.custom_configs[name])
            else:
                self.providers.pop(name, None)
            self._save_custom_configs()
            return True
        elif name in self.providers and not enabled:
            # Built-in platform disabling
            self.providers.pop(name, None)
            return True
        elif not enabled:
            return False
        else:
            self.load_all()
            return True

    def _save_custom_configs(self):
        data = [cfg.model_dump() for cfg in self.custom_configs.values()]
        with open(self.custom_platforms_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def list_platforms(self) -> List[Dict[str, Any]]:
        """Returns a list of all platforms with metadata."""
        output = []

        # Built-ins
        builtins = ["ats_direct", "linkedin", "indeed", "wellfound", "naukri", "internshala"]
        for b in builtins:
            output.append({
                "name": b,
                "display_name": b.upper().replace("_", " "),
                "type": "builtin",
                "enabled": b in self.providers,
                "source": "native"
            })

        # Custom JSON
        for name, cfg in self.custom_configs.items():
            output.append({
                "name": name,
                "display_name": cfg.display_name or name.capitalize(),
                "type": cfg.platform_type.value,
                "enabled": cfg.enabled and name in self.providers,
                "source": "custom_platforms.json",
                "url_template": cfg.url_template
            })

        return output
