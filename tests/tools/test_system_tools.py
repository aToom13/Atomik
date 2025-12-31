import pytest
import os
from AtomBase.tools.files import write_file, read_file, list_files, delete_file, create_directory

class TestSystemTools:
    @pytest.fixture
    def workspace(self):
        """Setup workspace"""
        path = os.path.abspath("atom_workspace")
        os.makedirs(path, exist_ok=True)
        return path

    def test_file_operations(self, workspace):
        """Test write -> read -> list -> delete flow"""
        fname = "test_sys.txt"
        abs_path = os.path.join(workspace, fname)
        
        # Write
        assert "Success" in write_file.invoke({"filename": abs_path, "content": "System Test"})
        
        # Read
        content = read_file.invoke({"filename": abs_path})
        assert content == "System Test"
        
        # List
        files = list_files.invoke({"directory": workspace})
        assert fname in files
        
        # Delete
        assert "deleted" in delete_file.invoke({"filename": abs_path})
        assert not os.path.exists(abs_path)

    def test_directory_creation(self, workspace):
        """Test directory creation"""
        dirname = "subdir/testdir"
        abs_path = os.path.join(workspace, dirname)
        
        assert "created" in create_directory.invoke({"directory_path": abs_path})
        assert os.path.exists(abs_path)
        
        # Cleanup
        import shutil
        shutil.rmtree(os.path.join(workspace, "subdir"))
