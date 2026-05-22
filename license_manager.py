# src/axiom/license_manager.py

import os
from datetime import datetime

class LicenseManager:
    """Gerencia validação silenciosa de licença proprietária AXIOM"""
    
    @staticmethod
    def validate_license():
        """
        Valida se arquivo LICENSE.txt existe no diretório raiz.
        SILENCIOSO - não exibe mensagens.
        """
        license_file = "LICENSE.txt"
        
        if not os.path.exists(license_file):
            raise PermissionError(
                "LICENSE.txt não encontrado. Coloque na raiz do projeto."
            )
        
        # Log silencioso (opcional)
        LicenseManager._log_usage()
        return True
    
    @staticmethod
    def _log_usage():
        """Log silencioso de uso (opcional)"""
        try:
            log_file = ".axiom_usage.log"
            timestamp = datetime.now().isoformat()
            with open(log_file, "a") as f:
                f.write(f"{timestamp} - App inicializado\n")
        except:
            pass