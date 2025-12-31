"""
Unified Code Quality Tool
Combines linter, formatter, and test runner into a single tool.
"""
import os
import subprocess
import sys

def verify_code_quality(filepath: str, actions: list = None) -> str:
    """
    Verify and improve code quality for a given file.
    
    Args:
        filepath: Path to the file
        actions: List of actions to perform. Default: ['format', 'lint', 'test']
                 Options: 'format' (black), 'lint' (flake8), 'test' (pytest)
    
    Returns:
        Report string
    """
    if actions is None:
        actions = ['format', 'lint', 'test']
        
    if not os.path.exists(filepath):
        return f"❌ Dosya bulunamadı: {filepath}"
    
    report = []
    success = True
    
    # 1. Format (Auto-fix)
    if 'format' in actions and filepath.endswith(".py"):
        try:
            # Run black
            result = subprocess.run(
                [sys.executable, "-m", "black", filepath],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                report.append(f"✅ Format (Black): Başarılı")
            else:
                report.append(f"⚠️ Format (Black): {result.stderr.strip()[:200]}...")
        except Exception as e:
            report.append(f"❌ Format Hatası: {str(e)}")

    # 2. Lint (Check only)
    if 'lint' in actions and filepath.endswith(".py"):
        try:
            # Run flake8
            result = subprocess.run(
                [sys.executable, "-m", "flake8", filepath, "--max-line-length=120", "--ignore=E501,W503"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                report.append(f"✅ Lint (Flake8): Temiz")
            else:
                success = False
                errors = result.stdout.strip()
                # Summarize errors if too long
                if len(errors) > 500:
                    errors = errors[:500] + "\n... (kısaltıldı)"
                report.append(f"❌ Lint Hataları:\n{errors}")
        except Exception as e:
            report.append(f"❌ Lint Hatası: {str(e)}")

    # 3. Test
    if 'test' in actions:
        try:
            # Decide what to test: the file itself or related tests
            target = filepath
            # If it's a source file (not test_), try to find corresponding test
            if not os.path.basename(filepath).startswith("test_") and filepath.endswith(".py"):
                # Simple heuristic: look for tests/test_filename.py
                dirname = os.path.dirname(filepath)
                basename = os.path.basename(filepath)
                possible_test = os.path.join(os.path.dirname(dirname), "tests", f"test_{basename}")
                if os.path.exists(possible_test):
                    target = possible_test
                elif os.path.exists(os.path.join(dirname, f"test_{basename}")):
                     target = os.path.join(dirname, f"test_{basename}")

            cmd = [sys.executable, "-m", "pytest", "-v", "--tb=short", target]
            
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60, cwd=os.getcwd()
            )
            
            if result.returncode == 0:
                report.append(f"✅ Testler (Pytest): Başarılı")
            else:
                success = False
                output = result.stdout + result.stderr
                if len(output) > 1000:
                    output = output[:1000] + "\n... (kısaltıldı)"
                report.append(f"❌ Test Başarısızlığı ({target}):\n{output}")
                
        except Exception as e:
            report.append(f"❌ Test Hatası: {str(e)}")

    status_icon = "✅" if success else "⚠️"
    return f"{status_icon} Kod Kalite Raporu ({os.path.basename(filepath)}):\n" + "\n".join(report)
