import adsk.core
import os
from ...lib import fusionAddInUtils as futil
from ... import config
app = adsk.core.Application.get()
ui = app.userInterface

# TODO *** Specify the command identity information. ***
CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_cmdDialog'
CMD_NAME = 'StackFuse'
CMD_Description = 'Computes a tolerance stack-up analysis using a monte carlo simulation to provide best/worst case scenarious for assemblies. \n\n Define the reference planes and type of measurement to compute. Define component planes by selecting the main points and axes, and define all tolerances and types for each component.'

# Specify that the command will be promoted to the panel.
IS_PROMOTED = True


root_inputs = None
arr = None

# try:
#     import numpy as np
# except:
#     import os
#     import sys
#     import subprocess
#     subprocess.check_call([os.path.join(sys.path[0], "Python", "python.exe"), "-m", "pip", "install", "--upgrade", "numpy"])
#     import numpy as np
#     futil.log("hi numpy")

# TODO *** Define the location where the command button will be created. ***
# This is done by specifying the workspace, the tab, and the panel, and the 
# command it will be inserted beside. Not providing the command to position it
# will insert it at the end.
WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID = 'SolidScriptsAddinsPanel'
COMMAND_BESIDE_ID = 'ScriptsManagerCommand'

# Resource location for command icons, here we assume a sub folder in this directory named "resources".
ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', '')

# Local list of event handlers used to maintain a reference so
# they are not released and garbage collected.
local_handlers = []


# Executed when add-in is run.
def start():
    # Create a command Definition.
    cmd_def = ui.commandDefinitions.addButtonDefinition(CMD_ID, CMD_NAME, CMD_Description, ICON_FOLDER)

    # Define an event handler for the command created event. It will be called when the button is clicked.
    futil.add_handler(cmd_def.commandCreated, command_created)

    # ******** Add a button into the UI so the user can run the command. ********
    # Get the target workspace the button will be created in.
    workspace = ui.workspaces.itemById(WORKSPACE_ID)

    # Get the panel the button will be created in.
    panel = workspace.toolbarPanels.itemById(PANEL_ID)

    # Create the button command control in the UI after the specified existing command.
    control = panel.controls.addCommand(cmd_def, COMMAND_BESIDE_ID, False)

    # Specify if the command is promoted to the main toolbar. 
    control.isPromoted = IS_PROMOTED

class Icons:
    def __init__(self):
        self.perp_icon = os.path.join(ICON_FOLDER, 'perp')
        self.conc_icon = os.path.join(ICON_FOLDER, 'conc')
        self.lin_icon = os.path.join(ICON_FOLDER, 'dim_lin')
        self.ang_icon = os.path.join(ICON_FOLDER, 'dim_ang')

ic=Icons()

# Executed when add-in is stopped.
def stop():
    # Get the various UI elements for this command
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    command_control = panel.controls.itemById(CMD_ID)
    command_definition = ui.commandDefinitions.itemById(CMD_ID)

    # Delete the button command control
    if command_control:
        command_control.deleteMe()

    # Delete the command definition
    if command_definition:
        command_definition.deleteMe()

    # Delete the panel if it is empty
    if panel.controls.count == 0:
        panel.deleteMe()


# Function that is called when a user clicks the corresponding button in the UI.
# This defines the contents of the command dialog and connects to the command related events.
def command_created(args: adsk.core.CommandCreatedEventArgs):
    futil.log(f'{CMD_NAME} Command Created Event')

    global arr
    arr = [] #array for tabs - will be needed later on

    inputs = args.command.commandInputs

    global root_inputs
    root_inputs = args.command.commandInputs

    # Fixed tab layout: just one default tab
    main_tab = inputs.addTabCommandInput('tab_main', 'Main')
    t1 = main_tab.children

    text_box_message = "<b>Reference Frame (Datums?)</b>"
    text_box_input = t1.addTextBoxCommandInput('main_title', 'Text Box', text_box_message, 1, True)
    text_box_input.isFullWidth = True

    # Add selection input
    selection_input = t1.addSelectionInput('selection_input', 'Reference Planes', 'Select 2 planes to measure the stack-up effect from.')
    selection_input.addSelectionFilter('PlanarFaces')
    selection_input.addSelectionFilter('ConstructionPlanes')
    selection_input.setSelectionLimits(2, 2) 

    # Add buttons
    button_row = t1.addButtonRowCommandInput('dim_type', 'Dimension Type', False)
    button_row.listItems.add('Item 1', False, ic.lin_icon)
    button_row.listItems.add('Item 2', False, ic.ang_icon)

    t1.addIntegerSpinnerCommandInput("tab_manager", "Num. Components", 1, 5, 1, 1)

    # # Add dropdown
    # perp_icon = ic.perp_icon
    # conc_icon = ic.conc_icon
    # dropdown = t1.addDropDownCommandInput('dropdown2', 'Dropdown 2', adsk.core.DropDownStyles.LabeledIconDropDownStyle)
    # dropdown.listItems.add('Perpendicular', False, perp_icon)
    # dropdown.listItems.add('Concentric', False, conc_icon)

    # # Add value inputs
    # default_unit = app.activeProduct.unitsManager.defaultLengthUnits
    # t1.addValueInput('upper_tol', 'Upper Tol.', default_unit, adsk.core.ValueInput.createByString('0.1'))
    # t1.addValueInput('lower_tol', 'Lower Tol.', default_unit, adsk.core.ValueInput.createByString('-0.1'))


    # Create integer spinner input
    # base_inputs.addIntegerSpinnerCommandInput("slider_controller2", "Num sliders", 1, 5, 1, 1)
    # updateTabs(inputs, base_inputs)

    # n = Tab("TeST", 'this is an id', inputs)
    # n.updateChildren()
    # arr.append(n)

    # Pre-create all possible tabs
    for i in range(5):
        id = f"component_{i}"
        tab = Tab(f"Comp. {i+1}", id, inputs)
        tab.object.isVisible = (i == 0)  # Show only the first by default
        arr.append(tab)

    # # Create tab input 3
    # tabCmdInput3 = inputs.addTabCommandInput('tab_3', 'Tab 3')
    # tab3ChildInputs = tabCmdInput3.children
    # # Create group
    # sliderGroup = tab3ChildInputs.addGroupCommandInput("slider_configuration", "Configuration")
    # sliderInputs = sliderGroup.children
    # # Create integer spinner input
    # sliderInputs.addIntegerSpinnerCommandInput("slider_controller", "Num sliders", 1, 5, 1, 1)
    # updateSliders(sliderInputs)


    # Hook up handlers
    futil.add_handler(args.command.inputChanged, command_input_changed, local_handlers=local_handlers)
    futil.add_handler(args.command.execute, command_execute, local_handlers=local_handlers)
    futil.add_handler(args.command.executePreview, command_preview, local_handlers=local_handlers)
    futil.add_handler(args.command.validateInputs, command_validate_input, local_handlers=local_handlers)
    futil.add_handler(args.command.destroy, command_destroy, local_handlers=local_handlers)


# def updateSliders(sliderInputs):
#     """
#     Populate 'slider_configuration' group with as many sliders as set in 'slider_controller'.
#     Delete previous ones and create new sliders.
#     """
#     spinner = sliderInputs.itemById("slider_controller")
#     value = spinner.value
#     # check ranges
#     if value > spinner.maximumValue or value < spinner.minimumValue:
#         return

#     # delete all sliders we have
#     toRemove = []
#     tr2 = []
#     for i in range(sliderInputs.count):
#         input = sliderInputs.item(i)
#         if input.objectType == adsk.core.FloatSliderCommandInput.classType():
#             toRemove.append(input)
#         if input.objectType == adsk.core.SelectionCommandInput.classType():
#             tr2.append(input)
    
#     # for input in toRemove:
#     #     input.deleteMe()
#     while len(toRemove)>(value):
#         input = toRemove[-1]
#         input.deleteMe()
#         toRemove = toRemove[:-1]

#         input = tr2[-1]
#         input.deleteMe()
#         toRemove = tr2[:-1]

#     # create new ones with range depending on total number
#     for i in range(len(toRemove), value):
#         id = str(i)
#         sliderInputs.addFloatSliderCommandInput("slider_configuration_" + id, "slider_" + id, "cm", 0, 10.0*value)
#         sliderInputs.addSelectionInput('selection_input' + id, 'Select Plane' + id, 'Select a Plane')
        

# def updateTabs(inputs, base_inputs):
#     """
    
#     """
#     spinner = base_inputs.itemById("slider_controller2")
#     value = spinner.value
#     # check ranges
#     if value > spinner.maximumValue or value < spinner.minimumValue:
#         return

#     # delete all sliders we have
#     toRemove = []
#     for i in range(inputs.count):
#         input = inputs.item(i)
#         if input.objectType == adsk.core.TabCommandInput.classType():
#             toRemove.append(input)
    
#     # for input in toRemove:
#     #     input.deleteMe()
#     while len(toRemove)>(value):
#         input = toRemove[-1]
#         input.deleteMe()
#         toRemove = toRemove[:-1]

#     # create new ones with range depending on total number
#     for i in range(len(toRemove), value):
#         id = str(i)
#         #sliderInputs.addFloatSliderCommandInput("slider_configuration_" + id, "slider_" + id, "cm", 0, 10.0*value)
#         n = inputs.addTabCommandInput(f'l{id}', f'm{id}')



# This event handler is called when the user clicks the OK button in the command dialog or 
# is immediately called after the created event not command inputs were created for the dialog.
def command_execute(args: adsk.core.CommandEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Command Execute Event')

    # TODO ******************************** Your code here ********************************

    # Get a reference to your command's inputs.
    inputs = args.command.commandInputs
    # text_box: adsk.core.TextBoxCommandInput = inputs.itemById('text_box')
    # value_input: adsk.core.ValueCommandInput = inputs.itemById('value_input')

    # # Do something interesting
    # text = text_box.text
    # expression = value_input.expression
    # msg = f'Your text: {text}<br>Your value: {expression}'
    # ui.messageBox(msg)


# This event handler is called when the command needs to compute a new preview in the graphics window.
def command_preview(args: adsk.core.CommandEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Command Preview Event')
    inputs = args.command.commandInputs


# This event handler is called when the user changes anything in the command dialog
# allowing you to modify values of other inputs based on that change.
def command_input_changed(args: adsk.core.InputChangedEventArgs):
    changed_input = args.input
    inputs = args.inputs

    futil.log(f'{CMD_NAME} Input Changed Event fired from a change to {changed_input.id}')

    if "controller" in changed_input.id:#changed_input.classType() == adsk.core.IntegerSpinnerCommandInput:# and "controller" in changed_input.id:
        #p('something changesd')
        for n in arr:
            n.updateChildren()

    elif changed_input.id == 'show_tab_checkbox':
        checkbox = adsk.core.BoolValueCommandInput.cast(inputs.itemById('show_tab_checkbox'))
        existing_tab = inputs.itemById('extra_tab')

        if checkbox.value:
            # Show the tab if it's not already added
            if not existing_tab:
                #ui.messageBox(f"Changed input f")
                new_tab = inputs.addTabCommandInput('extra_tab', 'Extra Tab')
                new_tab.children.addTextBoxCommandInput('info', 'Info', 'This is an extra tab.', 1, True)
                args.firingEvent.sender.parentCommand.doExecutePreview()
        else:
            # Remove the tab if it exists
            if existing_tab:
                #ui.messageBox(f"Changed input d")
                existing_tab.deleteMe()
                args.firingEvent.sender.parentCommand.doExecutePreview()


    elif 'tab_manager' in changed_input.id:
        value = changed_input.value
        for i, tab in enumerate(arr):
            tab.setEnabled(i < value)  # Show and enable first N tabs only

            
    # elif 'tab_manager' in changed_input.id:
    #     value = changed_input.value
    #     for i, tab in enumerate(arr):
    #         tab.object.isVisible = i < value
        # value = changed_input.value
        # if len(arr)>value: #more tabs exist than should exist
        #     pass #TODO Delete extra tabs
        # #p(f"{len(arr)}")
        # for i in range(len(arr), value):
        #     id = str(i)
        #     n = Tab(f"Comp. {id}", f'component_{id}', root_inputs)
        #     n.updateChildren()
        #     arr.append(n)

    # elif changed_input.id == "slider_controller":
    #     sliderGroup = adsk.core.GroupCommandInput.cast(changed_input.parentCommandInput)
    #     sliderInputs = sliderGroup.children
    #     updateSliders(sliderInputs)


class Tab:
    def __init__(self, name: str, id: str, inputs):
        #p(f"{inputs.classType()}")
        self.name = name
        self.id = id

        self.object = inputs.addTabCommandInput(self.id, self.name)
        self.c = self.object.children

        self.componentName = self.c.addTextBoxCommandInput('text_box_'+self.id, 'Component Name', 'Component', 1, False)

        self.pts = self.c.addSelectionInput('points_'+self.id, 'Select Points', 'Select 3 points to define the component plane.')
        self.pts.addSelectionFilter('Vertices')
        self.pts.addSelectionFilter('ConstructionPoints')
        self.pts.setSelectionLimits(3,3)
        # self.pts.addSelectionFilter('PlanarFaces')

        self.axs = self.c.addSelectionInput('axes_'+self.id, 'Select Axes', 'Select 3 corresponding axes to define the direction of transforamations.')
        self.axs.addSelectionFilter('ConstructionLines')
        self.axs.setSelectionLimits(0,3)
        # self.axs.addSelectionFilter('PlanarFaces')

        self.sectionGroup = self.c.addGroupCommandInput("tolerances_" + id, "Tolerances")
        self.sectionInputs = self.sectionGroup.children
        self.spinner = self.sectionInputs.addIntegerSpinnerCommandInput("controller"+"asdfjkasdjfkasjdflaskdjflakdfoweruowiefjalsdkjfalskdfjalsdkf"+id, "Num. Tolerances", 1, 5, 1, 1)

        if self.id!="component_0":
            self.setEnabled(False)

    def updateChildren(self):
        """
        Populate 'slider_configuration' group with as many sliders as set in 'slider_controller'.
        Delete previous ones and create new sliders.
        """
        value = self.spinner.value
        # check ranges
        if value > self.spinner.maximumValue or value < self.spinner.minimumValue:
            return

        # delete all sliders we have
        tr = []
        tr2 = []
        tr3 = []
        for i in range(self.sectionInputs.count):
            input = self.sectionInputs.item(i)
            if input.objectType == adsk.core.DropDownCommandInput.classType():
                tr.append(input)
            elif input.objectType == adsk.core.ValueCommandInput.classType():
                tr2.append(input)
            elif input.objectType == adsk.core.TextBoxCommandInput.classType():
                tr3.append(input)
        
        while len(tr)>(value):
            input = tr[-1]
            input.deleteMe()
            tr = tr[:-1]
            
            input = tr3[-1]
            input.deleteMe()
            tr3 = tr3[:-1]

            for i in range(2):
                input = tr2[-1]
                input.deleteMe()
                tr2 = tr2[:-1]

        #NEED TO ALSO ADD SELF.ID FOR MORE THAN ONE TABBB

        # create new ones with range depending on total number
        for i in range(len(tr), value):
            id = str(i)
            # self.sectionInputs.addFloatSliderCommandInput("slider_configuration_" + id, "slider_" + id, "cm", 0, 10.0*value)
            # self.sectionInputs.addSelectionInput('selection_input' + id, 'Select Plane' + id, 'Select a Plane')

            #text separator
            text_box_message = f"<b>Tolerance {int(id)+1}</b>"
            text_box_input = self.sectionInputs.addTextBoxCommandInput('text_box_input_'+id+self.id, 'Text Box', text_box_message, 1, True)
            text_box_input.isFullWidth = True

            # Add dropdown
            dropdown = self.sectionInputs.addDropDownCommandInput('dropdown_'+id+self.id, 'Tol. Type', adsk.core.DropDownStyles.LabeledIconDropDownStyle)
            dropdown.listItems.add('Perpendicular', True, ic.perp_icon)
            dropdown.listItems.add('Concentric', False, ic.conc_icon)

            # Add value inputs
            default_unit = app.activeProduct.unitsManager.defaultLengthUnits
            self.sectionInputs.addValueInput('upper_tol_'+id+self.id, 'Upper Tol.', default_unit, adsk.core.ValueInput.createByString('0.1'))
            self.sectionInputs.addValueInput('lower_tol_'+id+self.id, 'Lower Tol.', default_unit, adsk.core.ValueInput.createByString('-0.1'))

            #WILL need to do some tracking for ids for saving data later on
        
    def setEnabled(self, enabled: bool):
        self.object.isVisible = enabled
        self.object.isEnabled = enabled
        for i in range(self.c.count):
            input = self.c.item(i)
            input.isEnabled = enabled

        # Dynamically bypass validation for SelectionInputs
        if self.pts:
            if enabled:
                self.pts.setSelectionLimits(3, 3)
            else:
                self.pts.setSelectionLimits(0, 9999)  # Allow 0 when hidden

        if self.axs:
            if enabled:
                self.axs.setSelectionLimits(0   , 3)
            else:
                self.axs.setSelectionLimits(0, 9999)

        if self.sectionGroup:
            self.sectionGroup.isEnabled = enabled
            for i in range(self.sectionInputs.count):
                self.sectionInputs.item(i).isEnabled = enabled
    
    def kill_tab(self):
        self.object.deleteMe()


def p(msg):
    ui.messageBox(msg)


# This event handler is called when the user interacts with any of the inputs in the dialog
# which allows you to verify that all of the inputs are valid and enables the OK button.
# def command_validate_input(args: adsk.core.ValidateInputsEventArgs):
#     # General logging for debug.
#     futil.log(f'{CMD_NAME} Validate Input Event')

#     inputs = args.inputs
#     args.areInputsValid = True  # Default to true

#     for tab in arr:
#         if not tab.object.isVisible:
#             continue  # Skip hidden tabs

#         if tab.pts.selectionCount != 3 or tab.axs.selectionCount != 3:
#             args.areInputsValid = False
#             return

#     # # Verify the validity of the input values. This controls if the OK button is enabled or not.
#     # valueInput = inputs.itemById('value_input')
#     # if valueInput.value >= 0:
#     #     args.areInputsValid = True
#     # else:
#     #     args.areInputsValid = False

# def command_validate_input(args: adsk.core.ValidateInputsEventArgs):
#     # inputs = args.inputs
#     # name_input = adsk.core.TextBoxCommandInput.cast(inputs.itemById('main_name'))

#     # # Only validate main tab input
#     # if name_input and name_input.text.strip():
#     #     args.areInputsValid = True
#     # else:
#     #     args.areInputsValid = False
#     args.areInputsValid = True

def command_validate_input(args: adsk.core.ValidateInputsEventArgs):
    # Only validate inputs from the main tab (tab_main)
    inputs = args.inputs
    tab_main = inputs.itemById('tab_main')

    # Assume valid unless we find something invalid in the main tab
    args.areInputsValid = True

    # Validate only selection inputs in the main tab
    # for i in range(tab_main.children.count):
    #     input = tab_main.children.item(i)

    #     if input.objectType == adsk.core.SelectionCommandInput.classType():
    #         sel = adsk.core.SelectionCommandInput.cast(input)
    #         if sel.selectionCount < sel.minimumRequired or sel.selectionCount > sel.maximumAllowed:
    #             args.areInputsValid = False
    #             return
        

# This event handler is called when the command terminates.
def command_destroy(args: adsk.core.CommandEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Command Destroy Event')

    for n in arr:
        #p(f"{n.name}")
        n.kill_tab()

    global local_handlers
    local_handlers = []