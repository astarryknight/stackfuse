# StackFuse
Fusion 360 addin to compute tolerance stack-up analyses using Monte Carlo simulations.

![Helix Cover](./stackfuse.png)

# Installation
[Click here to download the Add-in](./dist/stackfuse.zip)

After downloading the zip file follow the [installation instructions here](https://tapnair.github.io/installation.html) for your particular OS version of Fusion 360 

## Usage:
This add-in makes tolerance analyses a breeze. Simply select the main plane you want to measure the effects on, and select a reference plane along with the type of measurement (angular or linear). 

For each contributor, create a ```component```. Each component is a plane defined by 3 points, and has 3 axes (which correspond to each respective point). These points and axes are used to calculate all of the tolerances from the contributor.

In each contributor, the user can add up to 5 ```tolerances```. Each tolerance is defined by its tolerance type and the upper and lower tolerance values.

## License
Samples are licensed under the terms of the [MIT License](http://opensource.org/licenses/MIT). Please see the [LICENSE](LICENSE) file for full details.

## Written by

Written by John Girgis <br /> (PPPL)
