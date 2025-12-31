"""
CalcoderPro - Gelişmiş Kod Üretim Sistemi
==========================================
- Self-healing (Kendi kendine hata düzeltme)
- Test-driven (Otomatik test)
- Iterative (Adım adım geliştirme)
- Multi-file (Çoklu dosya projeler)
"""
import os
import sys
import json
import re
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Project root
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORKSPACE_DIR = Path(os.path.join(_project_root, "atom_workspace"))
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)


logger = logging.getLogger("atomik.calcoder")

# Gemini client for code generation
try:
    from google import genai
    from core.config import API_KEY
    _client = genai.Client(api_key=API_KEY)
    GENAI_AVAILABLE = True
except ImportError:
    _client = None
    GENAI_AVAILABLE = False
    logger.warning("Gemini API not available for CalcoderPro")


class CalcoderPro:
    """
    Gelişmiş kod üretim sistemi
    - Self-healing (Kendi kendine hata düzeltme)
    - Test-driven (Otomatik test)
    - Iterative (Adım adım geliştirme)
    """
    
    def __init__(self, progress_callback: Callable[[str], None] = None):
        self.models = {
            "planner": "gemini-3-flash-preview",
            "coder": "gemini-3-flash-preview",
            "tester": "gemini-3-flash-preview",
        }
        self.workspace = WORKSPACE_DIR
        self.max_fix_attempts = 3
        self.batch_size = 3  # Parallel file generation batch size
        self.progress_callback = progress_callback or self._default_progress
        
    def _default_progress(self, message: str):
        """Default progress logger"""
        logger.info(f"[Progress] {message}")
        
    def _notify(self, message: str):
        """Send progress notification"""
        self.progress_callback(message)
        
    def _load_prompt(self, _prompt_file: str, **kwargs) -> str:
        """Load prompt from file and format it"""
        try:
            # AtomBase/prompts directory
            if not getattr(self, "prompts_dir", None):
                 self.prompts_dir = Path(os.path.join(_project_root, "AtomBase", "prompts", "calcoder"))
            
            prompt_path = self.prompts_dir / _prompt_file
            if prompt_path.exists():
                logger.info(f"Loading prompt from: {prompt_path}")
                content = prompt_path.read_text(encoding='utf-8')
                formatted = content.format(**kwargs)
                logger.debug(f"Prompt loaded (len={len(formatted)}): {formatted[:50]}...")
                return formatted
            else:
                logger.warning(f"Prompt file not found: {_prompt_file} at {prompt_path}")
                return ""
        except Exception as e:
            logger.error(f"Error loading prompt {_prompt_file}: {e}")
            return ""
    
    def _call_model(self, model_key: str, prompt: str) -> str:
        """Make a call to Gemini API"""
        if not GENAI_AVAILABLE:
            raise RuntimeError("Gemini API not available")
        
        model_name = self.models.get(model_key, "gemini-3-flash-preview")
        
        try:
            response = _client.models.generate_content(
                model=model_name,
                contents=[{"role": "user", "parts": [{"text": prompt}]}]
            )
            return response.text
        except Exception as e:
            logger.error(f"Model call error: {e}")
            raise
    
    def generate_code(
        self,
        task: str,
        context: Optional[str] = None,
        complexity: str = "auto"
    ) -> Dict:
        """
        Akıllı kod üretimi
        
        Args:
            task: "Snake oyunu yaz"
            context: Ek bilgi
            complexity: simple/medium/complex/auto
        """
        logger.info(f"Generating code for: {task}")
        
        # 1. Karmaşıklık analizi
        if complexity == "auto":
            complexity = self._analyze_complexity(task)
        
        logger.info(f"Complexity: {complexity}")
        
        if complexity == "simple":
            return self._simple_generation(task, context)
        else:
            return self._complex_generation(task, context)
    
    def _analyze_complexity(self, task: str) -> str:
        """Görevin karmaşıklığını belirle"""
        prompt = self._load_prompt("calcoder_complexity.txt", task=task)
        
        try:
            result = self._call_model("planner", prompt)
            result = result.strip().lower()
            if result in ["simple", "medium", "complex"]:
                return result
            return "simple"  # Default
        except Exception:
            return "simple"
    
    def _simple_generation(self, task: str, context: Optional[str] = None) -> Dict:
        """Basit görevler için hızlı üretim"""
        context_str = f"\nEk Bağlam: {context}" if context else ""
        
        prompt = self._load_prompt("calcoder_simple.txt", task=task, context_str=context_str)
        
        try:
            code = self._call_model("coder", prompt)
            code = self._clean_code(code)
            filename = self._generate_filename(task)
            
            # Kaydet
            filepath = self.workspace / filename
            filepath.write_text(code, encoding='utf-8')
            
            # Test et
            test_result = self._test_code(filepath)
            
            if test_result["success"]:
                return {
                    "filename": filename,
                    "filepath": str(filepath),
                    "code": code,
                    "status": "success",
                    "message": "Kod başarıyla oluşturuldu ve test edildi."
                }
            else:
                # Hata varsa düzelt (Self-healing)
                logger.info(f"Code has error, attempting self-healing...")
                return self._smart_fix(filepath, test_result["error"], {})
                
        except Exception as e:
            logger.error(f"Code generation error: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _complex_generation(self, task: str, context: Optional[str] = None) -> Dict:
        """
        Karmaşık görevler için iterative üretim
        - Paralel dosya üretimi (batch)
        - Progress bildirimleri
        - Otomatik asset oluşturma
        """
        context_str = f"\nEk Bağlam: {context}" if context else ""
        
        # 1. Plan oluştur
        self._notify("📋 Plan oluşturuluyor...")
        plan = self._create_plan(task, context_str)
        
        if not plan or not plan.get("files"):
            self._notify("⚠️ Plan oluşturulamadı, basit mod'a geçiliyor...")
            return self._simple_generation(task, context)
        
        file_list = plan.get("files", [])
        total_files = len(file_list)
        self._notify(f"✅ Plan hazır: {total_files} dosya oluşturulacak")
        
        # 2. Proje klasörü oluştur
        project_name = self._generate_project_name(task)
        project_dir = self.workspace / project_name
        project_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Project folder created: {project_dir}")
        
        # 3. Paralel dosya üretimi (batch processing)
        files = {}
        errors = []
        
        # Batch'lere böl
        batches = [file_list[i:i + self.batch_size] for i in range(0, len(file_list), self.batch_size)]
        
        for batch_idx, batch in enumerate(batches):
            batch_start = batch_idx * self.batch_size + 1
            batch_end = min(batch_start + len(batch) - 1, total_files)
            self._notify(f"🔧 Dosyalar oluşturuluyor ({batch_start}-{batch_end}/{total_files})...")
            
            # Parallel file generation within batch
            with ThreadPoolExecutor(max_workers=self.batch_size) as executor:
                future_to_file = {}
                for file_info in batch:
                    filename = file_info.get("name", "main.py")
                    purpose = file_info.get("purpose", "")
                    future = executor.submit(
                        self._generate_single_file, 
                        task, filename, purpose, files
                    )
                    future_to_file[future] = filename
                
                for future in as_completed(future_to_file):
                    filename = future_to_file[future]
                    try:
                        result = future.result()
                        if result.get("code"):
                            files[filename] = result["code"]
                            self._notify(f"   ✓ {filename}")
                        else:
                            errors.append(f"{filename}: Kod üretilemedi")
                    except Exception as e:
                        errors.append(f"{filename}: {str(e)[:50]}")
        
        if not files:
            return {
                "status": "failed",
                "error": "Hiçbir dosya üretilemedi",
                "details": errors,
                "message": "❌ Kod üretimi başarısız. Farklı bir istek deneyin."
            }
        
        # 4. Dosyaları kaydet
        self._notify(f"💾 {len(files)} dosya kaydediliyor...")
        for filename, code in files.items():
            filepath = project_dir / filename
            filepath.write_text(code, encoding='utf-8')
        
        # 5. Oyun/Görsel proje ise asset klasörü oluştur
        if self._needs_assets(task):
            self._notify("🎨 Asset klasörü oluşturuluyor...")
            self._create_asset_placeholders(project_dir, task)
        
        # 6. COMPREHENSIVE VERIFY-FIX LOOP - Tüm hatalar çözülene kadar döngü
        self._notify("🧪 Kapsamlı test ve düzeltme başlıyor...")
        max_global_iterations = 5  # Maximum overall iterations
        
        for iteration in range(max_global_iterations):
            all_passed = True
            fixed_count = 0
            failed_files = []
            
            self._notify(f"   🔄 İterasyon {iteration + 1}/{max_global_iterations}")
            
            for filename, code in list(files.items()):
                filepath = project_dir / filename
                
                # Dosyayı tekrar oku (önceki iterasyonda güncellenmiş olabilir)
                if filepath.exists():
                    current_code = filepath.read_text(encoding='utf-8')
                else:
                    current_code = code
                    filepath.write_text(code, encoding='utf-8')
                
                # Test et
                test_result = self._test_code(filepath)
                
                if not test_result["success"]:
                    all_passed = False
                    error_msg = test_result.get("error", "Unknown error")
                    
                    # Bu dosyayı düzelt
                    self._notify(f"   ⚠️ {filename}: {error_msg[:60]}...")
                    
                    # Smart Fix: Sadece hatalı dosyayı değil, config dosyalarını da düzeltebilir
                    fixed = self._smart_fix(filepath, error_msg, files)
                    
                    if fixed.get("status") == "fixed":
                        target_file = fixed.get("target_file", filename)
                        files[target_file] = fixed["code"]
                        fixed_count += 1
                        self._notify(f"   ✓ {target_file} düzeltildi")
                    else:
                        failed_files.append(filename)
                        self._notify(f"   ❌ {filename} düzeltilemedi")
            
            # Tüm dosyalar sözdizimsel olarak başarılı mı?
            if all_passed:
                # Syntax OK, şimdi Runtime Verification (TDD) zamanı!
                self._notify(f"   🏃‍♂️ Sözdizimi temiz, Çalışma Zamanı (Runtime) testi yapılıyor...")
                
                # Giriş noktasını bul (şimdilik main.py varsayımı)
                entry_point = "main.py"
                if not (project_dir / entry_point).exists():
                     # Eğer main.py yoksa, belki başka bir .py dosyasıdır.
                     py_files = list(project_dir.glob("*.py"))
                     if py_files:
                         entry_point = py_files[0].name
                
                verify_res = self._verify_execution(project_dir, entry_point)
                
                if verify_res["status"] == "failed":
                    all_passed = False
                    
                    failed_file_name = verify_res.get("failed_file", entry_point)
                    if not failed_file_name: failed_file_name = entry_point
                    
                    error_msg = verify_res.get("error", "Unknown Runtime Error")
                    error_summary = verify_res.get("error_summary", "Execution failed")
                    
                    self._notify(f"   🛑 Runtime Hatası ({failed_file_name}): {error_summary}")
                    
                    # Smart Fix uygula
                    filepath = project_dir / failed_file_name
                    fixed = self._smart_fix(filepath, error_msg, files)
                    
                    if fixed.get("success"):
                        target_file = fixed.get("fixed_file", failed_file_name)
                        files[target_file] = fixed["code"]
                        fixed_count += 1
                        self._notify(f"   ✓ {target_file} (Runtime hatası) düzeltildi")
                    else:
                        failed_files.append(failed_file_name)
                        self._notify(f"   ❌ {failed_file_name} düzeltilemedi")
                else:
                    self._notify(f"   ✅ Runtime testi başarılı! (TDD Passed)")
                    break

            if iteration < max_global_iterations - 1 and (fixed_count > 0 or not all_passed):
                self._notify(f"   🔧 {fixed_count} dosya düzeltildi, tekrar kontrol ediliyor...")
            else:
                if failed_files:
                    self._notify(f"   ⚠️ {len(failed_files)} dosya düzeltilemedi: {', '.join(failed_files[:3])}")
                break
        
        # 7. Proje bütünlüğünü kontrol et (eksik dosyalar, importlar)
        self._notify("🔍 Proje bütünlüğü kontrol ediliyor...")
        missing_deps = self._check_project_integrity(project_dir, files)
        if missing_deps:
            self._notify(f"   ⚠️ Eksik bağımlılıklar tespit edildi: {', '.join(missing_deps[:3])}")
            # Eksik dosyaları oluşturmaya çalış
            for dep in missing_deps[:3]:  # Max 3 eksik dosya
                self._notify(f"   📝 {dep} oluşturuluyor...")
                try:
                    self._create_missing_file(project_dir, dep, task, files)
                except Exception as e:
                    logger.warning(f"Could not create {dep}: {e}")
        
        # 8. Sonuç mesajı oluştur
        status_emoji = "✅" if all_passed else "🔧"
        if errors or failed_files:
            status_emoji = "⚠️"
        
        message = f"{status_emoji} {len(files)} dosya oluşturuldu"
        if fixed_count > 0:
            message += f" ({fixed_count} otomatik düzeltme)"
        message += f"\n📁 Konum: {project_name}/"
        
        if failed_files:
            message += f"\n⚠️ Düzeltilemeyenler: {', '.join(failed_files[:3])}"
        
        return {
            "files": files,
            "project_name": project_name,
            "project_dir": str(project_dir),
            "filepath": str(project_dir),
            "status": "success" if all_passed else ("partial" if files else "failed"),
            "message": message,
            "errors": errors if errors else None,
            "failed_files": failed_files,
            "stats": {
                "total_files": len(files),
                "fixed_count": fixed_count,
                "error_count": len(errors),
                "iterations": iteration + 1
            }
        }
    
    def _needs_assets(self, task: str) -> bool:
        """Görev asset gerektiriyor mu kontrol et"""
        asset_keywords = [
            "oyun", "game", "pygame", "görsel", "visual",
            "sprite", "animasyon", "animation", "flappy", "snake",
            "platform", "arcade", "resim", "image"
        ]
        task_lower = task.lower()
        return any(keyword in task_lower for keyword in asset_keywords)
    
    def _create_asset_placeholders(self, project_dir: Path, task: str):
        """Oyunlar için placeholder asset dosyaları oluştur"""
        try:
            # Asset generator script oluştur
            # task değişkenini generator script içine göm
            generator_code = f'''#!/usr/bin/env python3
"""
Placeholder Asset Generator
Run this once to create required game assets
"""
import os

try:
    import pygame
    pygame.init()
    
    IMG_DIR = os.path.dirname(os.path.abspath(__file__))
    
    def create_placeholder(name, size=(32, 32), color=(255, 100, 100)):
        surf = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.rect(surf, color, (0, 0, size[0], size[1]))
        pygame.draw.rect(surf, (0, 0, 0), (0, 0, size[0], size[1]), 2)
        pygame.image.save(surf, os.path.join(IMG_DIR, name))
        print(f"Created: {name}")
    
    # Context-aware asset generation
    task_name = "{task}".lower()
    
    if "snake" in task_name or "yılan" in task_name:
        create_placeholder("snake_head.png", (20, 20), (0, 255, 0))
        create_placeholder("snake_body.png", (20, 20), (0, 200, 0))
        create_placeholder("food.png", (15, 15), (255, 0, 0))
        create_placeholder("background.png", (800, 600), (30, 30, 30))
        print("🐍 Snake game assets created.")
        
    elif "flappy" in task_name or "bird" in task_name or "uçan" in task_name:
        create_placeholder("bird.png", (34, 24), (255, 220, 40))
        create_placeholder("pipe.png", (52, 320), (34, 139, 34))
        create_placeholder("ground.png", (336, 112), (222, 216, 149))
        create_placeholder("bg.png", (288, 512), (135, 206, 235))
        print("🐦 Flappy bird assets created.")
        
    else:
        # Generic placeholders
        create_placeholder("player.png", (32, 32), (50, 100, 255))
        create_placeholder("enemy.png", (32, 32), (255, 50, 50))
        create_placeholder("background.png", (800, 600), (20, 20, 20))
        print("🎨 Generic game assets created.")
    
    print("\\n✅ Asset generation complete!")
    
except ImportError:
    print("Pygame not installed. Run: pip install pygame")
except Exception as e:
    print(f"Error: {e}")

if __name__ == "__main__":
    pass  # Assets created on import
'''
            
            generator_path = assets_dir / "generate_assets.py"
            generator_path.write_text(generator_code, encoding='utf-8')
            
            # Generator'ı çalıştır
            try:
                result = subprocess.run(
                    [sys.executable, str(generator_path)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=str(assets_dir)
                )
                if result.returncode == 0:
                    logger.info("Asset placeholders created successfully")
                else:
                    logger.warning(f"Asset generation warning: {result.stderr[:100]}")
            except Exception as e:
                logger.warning(f"Could not auto-generate assets: {e}")
                
        except Exception as e:
            logger.warning(f"Asset folder creation failed: {e}")
    
    def _check_project_integrity(self, project_dir: Path, files: Dict[str, str]) -> List[str]:
        """
        Proje bütünlüğünü kontrol et
        - Eksik import edilmiş modülleri bul
        - Config dosyalarını kontrol et
        """
        missing = []
        
        for filename, code in files.items():
            # Python import'larını bul
            import_pattern = r'^(?:from\s+(\w+)|import\s+(\w+))'
            imports = re.findall(import_pattern, code, re.MULTILINE)
            
            for imp in imports:
                module_name = imp[0] or imp[1]
                # Standart kütüphane veya pip modülü mü?
                if module_name in ['pygame', 'neat', 'numpy', 'os', 'sys', 'time', 
                                   'random', 'json', 're', 'typing', 'pathlib',
                                   'subprocess', 'collections', 'math', 'pickle']:
                    continue
                
                # Projede bu modül var mı?
                module_file = f"{module_name}.py"
                if module_file not in files:
                    module_path = project_dir / module_file
                    if not module_path.exists():
                        missing.append(module_file)
        
        # NEAT config dosyası kontrolü
        if any('neat' in code.lower() for code in files.values()):
            config_files = ['config-feedforward.txt', 'config.txt', 'neat_config.txt']
            has_config = any((project_dir / cf).exists() for cf in config_files)
            if not has_config and 'config-feedforward.txt' not in files:
                missing.append('config-feedforward.txt')
        
        return list(set(missing))
    
    def _create_missing_file(self, project_dir: Path, filename: str, task: str, existing_files: Dict[str, str]):
        """Eksik dosyayı oluştur"""
        
        # NEAT config dosyası ise hazır şablon kullan
        if 'config' in filename.lower() and filename.endswith('.txt'):
            config_content = """[NEAT]
fitness_criterion     = max
fitness_threshold     = 1000
pop_size              = 50
reset_on_extinction   = False

[DefaultGenome]
feed_forward            = True
initial_connection      = full
enabled_default         = True
enabled_mutate_rate     = 0.01
activation_default      = tanh
activation_mutate_rate  = 0.0
activation_options      = tanh
aggregation_default     = sum
aggregation_mutate_rate = 0.0
aggregation_options     = sum
bias_init_mean          = 0.0
bias_init_stdev         = 1.0
bias_max_value          = 30.0
bias_min_value          = -30.0
bias_mutate_power       = 0.5
bias_mutate_rate        = 0.7
bias_replace_rate       = 0.1
compatibility_disjoint_coefficient = 1.0
compatibility_weight_coefficient   = 0.5
conn_add_prob           = 0.5
conn_delete_prob        = 0.5
weight_init_mean        = 0.0
weight_init_stdev       = 1.0
weight_max_value        = 30
weight_min_value        = -30
weight_mutate_power     = 0.5
weight_mutate_rate      = 0.8
weight_replace_rate     = 0.1
node_add_prob           = 0.2
node_delete_prob        = 0.2
num_hidden              = 0
num_inputs              = 11
num_outputs             = 4
response_init_mean      = 1.0
response_init_stdev     = 0.0
response_max_value      = 30.0
response_min_value      = -30.0
response_mutate_power   = 0.0
response_mutate_rate    = 0.0
response_replace_rate   = 0.0

[DefaultSpeciesSet]
compatibility_threshold = 3.0

[DefaultStagnation]
species_fitness_func = max
max_stagnation       = 20
species_elitism      = 2

[DefaultReproduction]
elitism            = 2
survival_threshold = 0.2
"""
            filepath = project_dir / filename
            filepath.write_text(config_content, encoding='utf-8')
            logger.info(f"Created NEAT config: {filename}")
            return
        
        # Python modülü ise LLM ile oluştur
        if filename.endswith('.py'):
            module_name = filename[:-3]
            
            existing_context = "\n".join([
                f"--- {name} ---\n{code[:500]}" 
                for name, code in list(existing_files.items())[:3]
            ])
            
            prompt = self._load_prompt("calcoder_missing_file.txt", task=task, module_name=module_name, existing_context=existing_context)
            
            try:
                code = self._call_model("coder", prompt)
                code = self._clean_code(code)
                
                filepath = project_dir / filename
                filepath.write_text(code, encoding='utf-8')
                existing_files[filename] = code
                logger.info(f"Created missing module: {filename}")
            except Exception as e:
                logger.error(f"Failed to create {filename}: {e}")
    
    def _generate_project_name(self, task: str) -> str:
        """Görevden proje klasör adı oluştur"""
        # Kelimelerden anlamlı isim çıkar
        words = re.findall(r'\b[a-zA-Z]+\b', task)[:4]
        if not words:
            words = ["project"]
        
        # CamelCase veya snake_case
        name = "_".join(w.capitalize() for w in words)
        # Geçersiz karakterleri temizle
        name = re.sub(r'[^a-zA-Z0-9_]', '', name)
        
        return name or "Project"

    
    def _create_plan(self, task: str, context: str) -> Optional[Dict]:
        """Geliştirme planı oluştur"""
        prompt = self._load_prompt("calcoder_plan.txt", task=task, context=context)
        
        try:
            result = self._call_model("planner", prompt)
            logger.info(f"Planner raw response (first 300 chars): {result[:300]}")
            
            # Clean response
            result = result.strip()
            
            # Remove markdown code blocks if present
            if result.startswith("```"):
                result = re.sub(r'^```[a-z]*\n?', '', result)
                result = re.sub(r'\n?```$', '', result)
                result = result.strip()
            
            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                try:
                    plan = json.loads(json_match.group())
                    if "files" in plan and len(plan["files"]) > 0:
                        logger.info(f"Plan created with {len(plan['files'])} files")
                        return plan
                except json.JSONDecodeError as je:
                    logger.error(f"JSON parse error: {je}")
            
            # Fallback: Create default single-file plan
            logger.warning("Could not parse plan, creating default single-file plan")
            task_name = re.sub(r'[^a-z0-9_]', '_', task.lower()[:30])
            task_name = re.sub(r'_+', '_', task_name).strip('_') or "main"
            return {
                "files": [{"name": f"{task_name}.py", "purpose": task}],
                "dependencies": []
            }
            
        except Exception as e:
            logger.error(f"Plan creation error: {e}")
            # Return default plan instead of None
            return {
                "files": [{"name": "main.py", "purpose": task}],
                "dependencies": []
            }
    
    def _generate_single_file(
        self,
        task: str,
        filename: str,
        purpose: str,
        existing_files: Dict[str, str]
    ) -> Dict:
        """Tek bir dosya oluştur"""
        existing_str = ""
        if existing_files:
            existing_str = "\n\nMevcut dosyalar:\n"
            for name, code in existing_files.items():
                existing_str += f"--- {name} ---\n{code[:500]}...\n"
        
        prompt = self._load_prompt("calcoder_generate.txt", task=task, filename=filename, purpose=purpose, existing_str=existing_str)
        
        if not prompt:
            logger.error(f"Prompt generation failed for {filename}")
            return {"filename": filename, "code": "", "error": "Prompt failed"}

        logger.info(f"Generating code for {filename}...")
        try:
            code = self._call_model("coder", prompt)
            if not code:
                logger.error(f"Model returned empty code for {filename}")
                return {"filename": filename, "code": "", "error": "Empty model response"}
            
            logger.info(f"Code generated for {filename} (len={len(code)})")
            
            code = self._clean_code(code)
            return {"filename": filename, "code": code}
        except Exception as e:
            logger.error(f"File generation error: {e}")
            return {"filename": filename, "code": "", "error": str(e)}
    
    def _test_code(self, filepath: Path) -> Dict:
        """Kodu test et"""
        try:
            # 1. Syntax check
            with open(filepath, encoding='utf-8') as f:
                code = f.read()
                compile(code, str(filepath), 'exec')
            
            # 2. Kısa çalıştırma testi (timeout ile)
            # Run with timeout (5s is enough to detect crash-on-start)
            # Use strict timeout to avoid hanging on game loops
            # Env: Use virtual display (:99) to avoid popping up on user screen
            env = os.environ.copy()
            env["DISPLAY"] = ":99"
            
            result = subprocess.run(
                [sys.executable, str(filepath)],
                cwd=str(self.workspace),
                capture_output=True,
                text=True,
                timeout=5, # Changed timeout from 10 to 5 as per snippet
                env=env
            )
            
            if result.returncode == 0:
                return {"success": True, "output": result.stdout}
            else:
                return {
                    "success": False,
                    "error": result.stderr or "Unknown error"
                }
        
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"SyntaxError: {e.msg} (line {e.lineno})"
            }
        except subprocess.TimeoutExpired:
            # Timeout doesn't necessarily mean failure for long-running apps
            return {"success": True, "output": "Timeout (may be interactive app)"}
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _smart_fix(
        self,
        failed_file: Path,
        error: str,
        files: Dict[str, str],
        max_attempts: Optional[int] = None
    ) -> Dict:
        """
        Akıllı hata düzeltme (Self-healing Pro).
        Hata veren dosyayı ve proje bağlamını (configler dahil) analiz eder.
        Gerekirse kod yerine config dosyasını düzeltir.
        """
        max_attempts = max_attempts or self.max_fix_attempts
        failed_filename = failed_file.name
        
        # Proje bağlamını hazırla (Config dosyaları ve ilgili python dosyaları)
        context_snippets = []
        
        # 1. Ortam Analizi (Directory Listing) - Deep Debugging
        try:
             parent_dir = failed_file.parent
             if parent_dir.exists():
                 items = [p.name for p in parent_dir.glob('*')]
                 # Dosya listesini metin olarak ekle
                 dir_list_str = "\n".join(items)
                 context_snippets.append(f"--- CURRENT DIRECTORY LISTING ({parent_dir.name}) ---\n{dir_list_str}\n(Check this list if 'File Not Found' error occurs)")
        except Exception as e:
             logger.warning(f"Failed to list directory for context: {e}")

        for name, content in files.items():
            if name == failed_filename:
                continue
            
            # Sadece alakalı dosyaları al (txt, json, py)
            if name.endswith(('.txt', '.json', '.yaml', '.ini', '.py')):
                # Çok büyük dosyaları kırp
                preview = content if len(content) < 2000 else content[:1000] + "\n... (truncated)"
                context_snippets.append(f"--- {name} ---\n{preview}")
        
        project_context = "\n\n".join(context_snippets)
        original_code = files.get(failed_filename, "")
        if not original_code and failed_file.exists():
            original_code = failed_file.read_text(encoding='utf-8')

        for attempt in range(max_attempts):
            logger.info(f"Smart Fix attempt {attempt + 1}/{max_attempts} for {failed_filename}")
            
            prompt = self._load_prompt("calcoder_fix.txt", failed_filename=failed_filename, error=error, original_code=original_code, project_context=project_context)
            
            try:
                response = self._call_model("coder", prompt)
                # JSON temizle (bazen markdown içinde gelir)
                json_str = response.replace("```json", "").replace("```", "").strip()
                
                import json
                fix_data = json.loads(json_str)
                
                target_file = fix_data.get("target_file", failed_filename)
                new_content = fix_data.get("content", "")
                
                if not new_content:
                    raise ValueError("Empty content in fix response")
                
                # Dosyayı güncelle
                target_path = failed_file.parent / target_file
                target_path.write_text(new_content, encoding='utf-8')
                
                # Test et (Eğer python dosyasıysa test et, config ise ana dosyayı test et)
                test_target = target_path if target_path.name.endswith('.py') else failed_file
                test_result = self._test_code(test_target)
                
                if test_result["success"]:
                    return {
                        "status": "fixed",
                        "target_file": target_file,
                        "code": new_content,
                        "attempts": attempt + 1,
                        "message": f"Fixed {target_file}: {fix_data.get('explanation', 'Error resolved')}"
                    }
                else:
                    # Yeni hata ile devam et
                    error = f"Fix for {target_file} failed. New error:\n{test_result['error']}"
                    # Context'i güncelle
                    files[target_file] = new_content
            
            except Exception as e:
                logger.error(f"Fix attempt {attempt + 1} failed: {e}")
        
        return {
            "status": "failed",
            "error": f"Could not fix after {max_attempts} attempts."
        }
    
    def _clean_code(self, code: str) -> str:
        """Kod temizleme - markdown bloklarını kaldır"""
        # Remove ```python and ``` blocks
        code = re.sub(r'^```python\s*\n?', '', code, flags=re.MULTILINE)
        code = re.sub(r'^```\s*\n?', '', code, flags=re.MULTILINE)
        code = re.sub(r'\n```$', '', code)
        
        # Remove leading/trailing whitespace
        code = code.strip()
        
        return code
    
    def _generate_filename(self, task: str) -> str:
        """Görevden uygun dosya adı oluştur"""
        # Basit kelime çıkarma
        words = re.findall(r'\b[a-zA-Z]+\b', task.lower())[:3]
        if not words:
            words = ["main"]
        
        name = "_".join(words)
        # Geçersiz karakterleri kaldır
        name = re.sub(r'[^a-z0-9_]', '', name)
        
        return f"{name}.py"


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================
_calcoder: Optional[CalcoderPro] = None


def get_calcoder() -> CalcoderPro:
    """Global CalcoderPro instance"""
    global _calcoder
    if _calcoder is None:
        _calcoder = CalcoderPro()
    return _calcoder


# =============================================================================
# TOOL FUNCTIONS (for executor.py integration)
# =============================================================================
def write_code_advanced(
    task: str,
    complexity: str = "auto",
    context: str = None,
    test: bool = True
) -> Dict:
    """
    Gelişmiş kod yazma
    
    Args:
        task: "Snake oyunu yaz", "REST API oluştur"
        complexity: simple/medium/complex/auto
        context: Ek bilgi
        test: Otomatik test et mi?
    """
    calcoder = get_calcoder()
    result = calcoder.generate_code(task, context, complexity)
    return result


def fix_code_file(filename: str, error_message: str) -> Dict:
    """
    Hatalı kodu düzelt
    
    Args:
        filename: "snake_game.py" veya "ProjeAdi/main.py"
        error_message: Hata mesajı
    """
    calcoder = get_calcoder()
    
    # Önce direkt workspace'te ara
    filepath = calcoder.workspace / filename
    
    if not filepath.exists():
        # Proje klasörlerinde ara
        for subdir in calcoder.workspace.iterdir():
            if subdir.is_dir():
                candidate = subdir / filename
                if candidate.exists():
                    filepath = candidate
                    break
    
    if not filepath.exists():
        return {"status": "failed", "error": f"Dosya bulunamadı: {filename}"}
    
    result = calcoder._smart_fix(filepath, error_message, {})
    return result


def run_code_tests(filename: str) -> Dict:
    """
    Kodu test et
    
    Args:
        filename: "main.py" veya "ProjeAdi/main.py"
    """
    calcoder = get_calcoder()
    
    # Önce direkt workspace'te ara
    filepath = calcoder.workspace / filename
    
    if not filepath.exists():
        # Proje klasörlerinde ara
        for subdir in calcoder.workspace.iterdir():
            if subdir.is_dir():
                candidate = subdir / filename
                if candidate.exists():
                    filepath = candidate
                    break
    
    if not filepath.exists():
        return {"success": False, "error": f"Dosya bulunamadı: {filename}"}
    
    result = calcoder._test_code(filepath)
    return result
