# Simple API Tests

## Local run

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run smoke tests with Allure results:

```powershell
pytest -m smoke --alluredir=allure-results --clean-alluredir
```

## Docker run

Build the image:

```powershell
docker build -t simple-api-tests .
```

Run tests in the container:

```powershell
docker run --rm -e BASE_URL=https://testapi.intercars.ru/api/v1 -v ${PWD}/allure-results:/app/allure-results simple-api-tests
```

Run a custom test selection:

```powershell
docker run --rm -e BASE_URL=https://testapi.intercars.ru/api/v1 -v ${PWD}/allure-results:/app/allure-results simple-api-tests pytest tests/smoke/test_routes_search.py --alluredir=allure-results --clean-alluredir
```

## GitHub Actions

The workflow is stored in `.github/workflows/api-tests.yml`.

- Tests run inside Docker on every push to `main` or `master`
- Tests run on pull requests
- Manual runs support custom `pytest` arguments through `workflow_dispatch`
- `allure-results` are uploaded as build artifacts
- `allure-report` HTML is generated in CI
- On non-PR runs, the HTML report is uploaded as a GitHub Pages artifact and deployed to GitHub Pages

If needed, add `BASE_URL` in GitHub repository secrets.
To publish the report site, enable GitHub Pages in repository settings and select `GitHub Actions` as the source.

## Open Allure report locally

The Python package writes only `allure-results`. To render HTML, install the Allure CLI separately.

Temporary local server:

```powershell
allure serve allure-results
```

Generate static HTML report:

```powershell
allure generate allure-results -o allure-report --clean
```

## Notes

- `allure-results/` and `allure-report/` are ignored by git.
- Local `.venv/`, `.idea/`, `.env` and training files from `repit/` should not be committed.
- Copy `.env.example` to `.env` for local configuration.
