from main import app

def test_app_instance_exists():
    assert app is not None
    assert hasattr(app, "router")