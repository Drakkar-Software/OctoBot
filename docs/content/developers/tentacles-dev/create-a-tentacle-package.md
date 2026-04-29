---
title: "Create a tentacle package"
description: "Learn how to bundle your custom OctoBot tentacles in a tentacle package, enable configuration via user inputs, add associated docs and share it."
sidebar_position: 7
---



# Tentacle package development

## Tentacle packages

This page covers tentacle package creation. A working [Octobot developer environment](/developers/environment/setup-your-environment) is required to create a tentacle.

A tentacle package is a python module that contains one or multiple [tentacles](create-a-tentacle)
of the same type.

### The tentacle package folder

A tentacle package is defined by a folder located at :

```bash
tentacles/YOUR_TP_CATEGORY/YOUR_TP_SUB_CATEGORY/YOUR_TENTACLE_PACKAGE_NAME/
```

> TP is for tentacle package

- **YOUR_TP_CATEGORY** can be Backtesting, Evaluator, Services or Trading

- **YOUR_TP_SUB_CATEGORY** should be a sub category of **YOUR_TP_CATEGORY** in the existing
  tentacle architecture

- **YOUR_TENTACLE_PACKAGE_NAME** is the name of your tentacle package, shouldn't use an
  existing tentacle package name

### Description file

A tentacle package contains metadata described in the metadata.json file. This file is
used to properly install the tentacle and should be carefully written. It's located at
the root path of the tentacle package :

```bash
tentacles/YOUR_TP_CATEGORY/YOUR_TP_SUB_CATEGORY/YOUR_TENTACLE_PACKAGE_NAME/metadata.json
```

A tentacle package metadata.json contains :

```javascript
{
  "version": "YOUR_TP_VERSION",
  "origin_package": "YOUR_TP_ORIGIN_PACKAGE",
  "tentacles": ["YOUR_TP_TENTACLE_1", "YOUR_TP_TENTACLE_2"],
  "tentacles-requirements": ["YOUR_TP_TP_REQUIREMENT_1", "YOUR_TP_TP_REQUIREMENT_2"]
}
```

- **YOUR_TP_VERSION** is your tentacle package version
- **YOUR_TP_ORIGIN_PACKAGE** is the author or the origin repository of the tentacle package

- **YOUR_TP_TENTACLE_1** and **YOUR_TP_TENTACLE_2** are name of the tentacle classes contained
  in your tentacle package tentacles (1 or more).

- **YOUR_TP_TP_REQUIREMENT_1** and **YOUR_TP_TP_REQUIREMENT_2** are the names of required
  tentacle packages to have installed to run your tentacle package (0 or more)

> **YOUR_TP_TENTACLE_X** should match python classes to be exposed in the tentacle

Example _DailyTradingMode/metadata.json_ :

```javascript
{
  "version": "1.2.0",
  "origin_package": "OctoBot-Default-Tentacles",
  "tentacles": ["DailyTradingMode"],
  "tentacles-requirements": ["mixed_strategies_evaluator"]
}
```

### Tentacle modules

[Tentacle](create-a-tentacle) python modules should be placed at the root path of the
tentacle package. There can 1 or more modules per package.

Example with _momentum_evaluator_ : The main python module that contains multiple tentacles
is located at

```bash
tentacles/Evaluator/TA/momentum_evaluator/momentum.py
```

Every tentacle classes should be imported in the package root `__init__.py` file.

Example with _momentum_evaluator_'s `__init__.py`.py :

```python
from .momentum import RSIMomentumEvaluator, ADXMomentumEvaluator, RSIWeightMomentumEvaluator,
BBMomentumEvaluator, MACDMomentumEvaluator, KlingerOscillatorMomentumEvaluator,
KlingerOscillatorReversalConfirmationMomentumEvaluator
```

### Configuration

A tentacle package can contain tentacle configurations.
Tentacles configuration consists in 2 parts:

1. User inputs: the description of each configuration parameter, in the `init_user_inputs` tentacle method
2. Default configuration: the default configuration values, as json, in the `config` folder

#### User inputs

On OctoBot's web interface, tentacle configuration settings are generated using their definition
as User inputs as well as their current values.

For a configuration parameter to show on the configuration interface, it has to be defined as
user input. Any value contained in the json configuration file can be used by the tentacle but
only the ones associated to user inputs will be visible to the user.

```python
def init_user_inputs(self, inputs: dict) -> None:
   self.period_length = self.UI.user_input(
        "period_length", enums.UserInputTypes.INT, 14, inputs,
        min_val=1, title="EMA period length."
    )
    self.min_trigger_value = self.UI.user_input(
        "sleep_delay", enums.UserInputTypes.FLOAT, 0.5, inputs,
        min_val=0.34, max_val=0.75, title="Threshold above which to trigger a signal."
    )
    self.send_notification = self.UI.user_input(
        "send_notification", enums.UserInputTypes.BOOLEAN, True, inputs,
        title="When enabled, send telegram notification on signal."
    )
```

The full definition of user inputs can be found

<a href="https://github.com/Drakkar-Software/OctoBot-Commons/blob/master/octobot_commons/configuration/user_inputs.py" rel="nofollow">here</a>
.

If you are unsure how to use user inputs, have a look at

<a href="https://github.com/Drakkar-Software/OctoBot-Tentacles/blob/master/Evaluator/TA/momentum_evaluator/momentum.py" rel="nofollow">the existing tentacles user inputs</a>
.

> Tentacles configuration are displayed using the <a href="https://github.com/json-editor/json-editor" rel="nofollow">json-editor</a>
> library. User inputs are converted into json schemas that are then passed to the editor alongside
> their current configuraiton values.

- The `editor_options` argument allows to set json-editor specific options such as the `disable_array_add` option (`editor_options={"disable_array_add": True}`).
- The `other_schema_values` argument allows to set json schema specific parameters such as the `minItems` or `uniqueItems` for arrays (`other_schema_values={"minItems": 1, "uniqueItems": True}`).

#### Default configuration

Values for an tentacle default configuration are located in the _config/_ folder at :

```bash
tentacles/YOUR_TP_CATEGORY/YOUR_TP_SUB_CATEGORY/YOUR_TENTACLE_PACKAGE_NAME/config/
```

Each tentacles config file should be named with the exact case and name as the associated
tentacle class. Below an example for _MyAwesomeTentacle_ :

```bash
tentacles/YOUR_TP_CATEGORY/YOUR_TP_SUB_CATEGORY/YOUR_TENTACLE_PACKAGE_NAME/config/MyAwesomeTentacle.json
```

Once a tentacle configuration has been edited, a local copy of this json configuration file
is added to your profile where local changes are saved.

### Resources

Tentacle resources are located in the **resources** folder of your tentacle package.

Each tentacles documentation should be created for in `resources/YOUR_TP_TENTACLE_1.md`,
`resources/YOUR_TP_TENTACLE_2.md` (the file name should match the tentacle class name).

A tentacle package can also contain many resources that can be binary files, images...

Example _DailyTradingMode/resources/DailyTradingMode.md_ :

```text
DailyTradingMode is a **low risk versatile trading mode** that reacts only the its state changes to
a state that is different from the previous one and that is not NEUTRAL.

When triggered for a given symbol, it will cancel previously created (and unfilled) orders
and create new ones according to its new state.

DailyTradingMode will consider every compatible strategy and average their evaluation to create
each state.
```

> You can use <a href="https://www.markdownguide.org/cheat-sheet" rel="nofollow">markdown</a> to format a
> tentacle documentation.

### Tests

Tentacle should be tested. Tests file are usually located in the **tests** folder
of the tentacle package.

## Installing and sharing tentacles

Follow the [tentacles installation guide](customize-your-octobot) to install or
share your custom tentacle package.
