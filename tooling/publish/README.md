

## Publication

-    activate .publish_venv
-    navigate in py-youwol folder
-    new version?
-    move content of *dist* in *old_dist*
-    ```python setup.py clean --all```
-    ```python setup.py sdist bdist_wheel```
-    ```twine check dist/*```
-    test on test.pypi: ```twine upload --repository-url https://test.pypi.org/legacy/dist/*```
-    finally: ```twine upload dist/*```

https://realpython.com/pypi-publish-python-package/
