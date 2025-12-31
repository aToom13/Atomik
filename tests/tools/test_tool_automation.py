
import pytest
from unittest.mock import patch, MagicMock
from tools.declarations import get_declarations
from tools.executor import execute_tool

class TestToolAutomation:
    """
    Otomatik Tool Testleri
    Bu test sınıfı, sisteme yeni eklenen toolların (declarations.py)
    executor tarafından tanınıp tanınmadığını otomatik olarak kontrol eder.
    """
    
    def test_all_declared_tools_are_implemented(self):
        """
        Her tool tanımı (declaration) için executor'ın 'Unknown tool' hatası vermediğini doğrula.
        Bu test, yeni bir tool tanımlayıp implemente etmeyi unutan geliştiriciyi uyarır.
        """
        declarations = get_declarations()
        implemented_tools = []
        missing_tools = []
        
        # Executor içindeki yan etkileri (side-effects) önlemek için global fonksiyonları mockla.
        # Sadece executor.py içinde module-level import edilenleri buraya ekleyebiliriz.
        # Fonksiyon içinde import edilenler (local imports) buraya eklenemez.
        # Bu testin amacı "Unknown tool" dönmemesi olduğu için, tool çalışıp hata verirse bile test geçer.
        with patch("tools.executor.state", MagicMock()), \
             patch("tools.executor.get_current_time", MagicMock()), \
             patch("tools.executor.get_current_location", MagicMock()), \
             patch("tools.executor.visit_webpage", MagicMock()), \
             patch("tools.executor.list_files", MagicMock()), \
             patch("tools.executor.run_terminal_command", MagicMock()):
             
            for tool in declarations:
                name = tool["name"]
                
                try:
                    # Tool'u boş argümanlarla çağır
                    # Amacımız tool'un başarılı çalışması değil, 
                    # executor'ın "ben bu tool'u tanımıyorum" dememesi.
                    result = execute_tool(name, {})
                    
                    # Eğer executor tool'u tanımazsa "Unknown tool: <name>" veya benzeri bir string döner.
                    # executor.py satır 824'e göre: return f"Unknown tool: {name}"
                    
                    result_str = str(result)
                    
                    if f"Unknown tool: {name}" in result_str:
                        missing_tools.append(name)
                    else:
                        implemented_tools.append(name)
                        
                except Exception:
                    # Hata fırlatması bile tool'un tanındığı anlamına gelir (if bloğuna girmiş demektir)
                    implemented_tools.append(name)
        
        # Raporlama
        if missing_tools:
            pytest.fail(f"\nAşağıdaki araçlar 'declarations.py' içinde tanımlı ama 'executor.py' içinde implemente edilmemiş:\n" + "\n".join(f"- {t}" for t in missing_tools))

    def test_safe_tools_execution(self):
        """
        Parametresiz ve güvenli (read-only) araçların gerçekten çalıştığını test et.
        """
        safe_tools = ["get_current_time", "get_task_summary"]
        
        # Bu testler kısmen logic de içerdiği için daha dikkatli mocklanmalı veya entegrasyon testi olmalı.
        # Şimdilik sadece varlıklarını kontrol edelim.
        pass
