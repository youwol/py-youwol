
# Start YouWol


The full list of command line options to start youwol is described in 
[MainArguments](@nav/references/youwol/app.main_args.MainArguments), it can also be displayed using `youwol -help`.

The most important parameter is `--conf`: it defines the server's configuration file.
When starting youwol, it searches for the configuration file in the following order:

*  If the `--conf` option is provided, youwol will use the specified configuration file,
for example `youwol --conf=/path/to/file.py`.
*  If the `--conf` option is not provided, youwol looks for a file named `yw_config.py` in the current 
directory and boot from it if found.
*  If neither of the above options are successful, youwol will create a default configuration 
file called `yw_config.py` in the current directory and boot from it.

The configuration file is a python file that either:

*  yields a [Configuration](@nav/references/youwol/app/environment/models.models_config.Configuration) as last statement:

```python
from youwol.app.environment import Configuration

Configuration()
```

*  defines a `ConfigurationFactory` class implementing
   [IConfigurationFactory](@nav/references/youwol/app/environment.config_from_module.IConfigurationFactory):

```python
from youwol.app.environment import Configuration, IConfigurationFactory
from youwol.app.main_args import MainArguments

class ConfigurationFactory(IConfigurationFactory):
   
    async def get(self, _main_args: MainArguments):
        return Configuration()

```
