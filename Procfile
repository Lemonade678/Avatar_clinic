web: PYTHONPATH=src uvicorn stockcount.app:build_default_app --factory --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips "*"
