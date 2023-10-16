from projen.awscdk import AwsCdkPythonApp

project = AwsCdkPythonApp(
    author_email="cullancarey@gmail.com",
    author_name="Cullan Carey",
    cdk_version="2.1.0",
    module_name="PortfolioWebsite",
    name="PortfolioWebsite",
    version="0.1.0",
)

project.synth()