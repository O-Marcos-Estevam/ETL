"""
Config Manager - Gerenciamento de Configurações
================================================

Responsável por carregar, salvar e gerenciar configurações
da aplicação (caminhos, credenciais, sistemas ativos).
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class SystemConfig:
    """Configuração de um sistema individual."""
    enabled: bool = False
    name: str = ""


@dataclass
class CredentialConfig:
    """Credenciais de um sistema."""
    username: str = ""
    password: str = ""
    url: str = ""


class ConfigManager:
    """
    Gerenciador de configurações da aplicação.
    
    Carrega e salva configurações em JSON, com fallback
    para valores padrão se o arquivo não existir.
    """
    
    DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "resources" / "config.json"
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Inicializa o gerenciador de configurações.
        
        Args:
            config_path: Caminho do arquivo de configuração.
                        Se None, usa o padrão em resources/config.json
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self._config: Dict[str, Any] = {}
        self.load()
    
    def load(self) -> bool:
        """
        Carrega configurações do arquivo JSON.
        
        Returns:
            True se carregou com sucesso, False caso contrário
        """
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
                return True
            else:
                self._config = self._get_default_config()
                self.save()
                return True
        except Exception as e:
            print(f"Erro ao carregar config: {e}")
            self._config = self._get_default_config()
            return False
    
    def save(self) -> bool:
        """
        Salva configurações no arquivo JSON.
        
        Returns:
            True se salvou com sucesso, False caso contrário
        """
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Erro ao salvar config: {e}")
            return False
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Retorna configuração padrão."""
        return {
            "app": {
                "name": "ETL Pipeline Manager",
                "version": "1.0.0",
                "theme": "dark"
            },
            "paths": {
                "database": "",
                "xml_folder": "",
                "pdf_folder": "",
                "excel_folder": "",
                "downloads_aux": "",
                "bd_aux": "",
                "temp_downloads": ""
            },
            "systems": {
                "amplis": {"enabled": False, "name": "Amplis"},
                "maps": {"enabled": False, "name": "MAPS"},
                "fidc_estoque": {"enabled": False, "name": "FIDC Estoque"},
                "jcot": {"enabled": False, "name": "JCOT"},
                "britech": {"enabled": False, "name": "Britech"},
                "qore_pdf": {"enabled": False, "name": "QORE PDF"},
                "qore_excel": {"enabled": False, "name": "QORE Excel"},
                "qore_xml": {"enabled": True, "name": "QORE XML"},
                "xml_upload": {"enabled": True, "name": "XML Upload"}
            },
            "credentials": {}
        }
    
    # =========================================================================
    # GETTERS
    # =========================================================================
    
    def get(self, key: str, default: Any = None) -> Any:
        """Obtém valor de configuração por chave (suporta notação de ponto)."""
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def get_path(self, key: str) -> Path:
        """Obtém um caminho de configuração."""
        return Path(self.get(f"paths.{key}", ""))
    
    def get_system(self, key: str) -> Dict[str, Any]:
        """Obtém configuração de um sistema."""
        return self.get(f"systems.{key}", {"enabled": False, "name": key})
    
    def is_system_enabled(self, key: str) -> bool:
        """Verifica se um sistema está habilitado."""
        return self.get(f"systems.{key}.enabled", False)
    
    def get_credential(self, system: str, field: str) -> str:
        """Obtém uma credencial específica."""
        return self.get(f"credentials.{system}.{field}", "")
    
    # =========================================================================
    # SETTERS
    # =========================================================================
    
    def set(self, key: str, value: Any) -> None:
        """Define valor de configuração por chave (suporta notação de ponto)."""
        keys = key.split('.')
        target = self._config
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value
    
    def set_system_enabled(self, key: str, enabled: bool) -> None:
        """Define se um sistema está habilitado."""
        self.set(f"systems.{key}.enabled", enabled)
    
    def set_credential(self, system: str, field: str, value: str) -> None:
        """Define uma credencial específica."""
        self.set(f"credentials.{system}.{field}", value)
    
    # =========================================================================
    # BULK OPERATIONS
    # =========================================================================
    
    def get_enabled_systems(self) -> list:
        """Retorna lista de sistemas habilitados."""
        systems = self.get("systems", {})
        return [key for key, val in systems.items() if val.get("enabled", False)]
    
    def set_all_systems(self, enabled: bool) -> None:
        """Habilita ou desabilita todos os sistemas."""
        systems = self.get("systems", {})
        for key in systems:
            self.set_system_enabled(key, enabled)


# Instância global (opcional)
config = ConfigManager()
