import adsk.core
import os
from ...lib import fusionAddInUtils as futil
from ... import config
import json
app = adsk.core.Application.get()
ui = app.userInterface

# TODO *** Specify the command identity information. ***
CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_cmdDialog'
CMD_NAME = 'StackFuse'
CMD_Description = 'Computes a tolerance stack-up analysis using a monte carlo simulation to provide best/worst case scenarious for assemblies. \n\n Define the reference planes and type of measurement to compute. Define component planes by selecting the main points and axes, and define all tolerances and types for each component.'

# Specify that the command will be promoted to the panel.
IS_PROMOTED = True

# init global variables
root_inputs = None
tabs = None

# TODO *** Define the location where the command button will be created. ***
# This is done by specifying the workspace, the tab, and the panel, and the 
# command it will be inserted beside. Not providing the command to position it
# will insert it at the end.
WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID = 'SolidScriptsAddinsPanel'
COMMAND_BESIDE_ID = 'ScriptsManagerCommand'

# Resource location for command icons, here we assume a sub folder in this directory named "resources".
ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', '')

# easy access to icons
class Icons:
    def __init__(self):
        self.perp_icon = os.path.join(ICON_FOLDER, 'perp')
        self.conc_icon = os.path.join(ICON_FOLDER, 'conc')
        self.lin_icon = os.path.join(ICON_FOLDER, 'dim_lin')
        self.ang_icon = os.path.join(ICON_FOLDER, 'dim_ang')

ic=Icons()

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

    global tabs
    tabs = [] #array for tabs - will be needed later on

    inputs = args.command.commandInputs

    global root_inputs
    root_inputs = args.command.commandInputs

    #main tab
    main_tab = inputs.addTabCommandInput('tab_main', 'Main')
    t1 = main_tab.children

    text_box_message = "<b>Reference Frame (Datums?)</b>"
    text_box_input = t1.addTextBoxCommandInput('main_title', 'Text Box', text_box_message, 1, True)
    text_box_input.isFullWidth = True

    # Add selection input
    selection_input = t1.addSelectionInput('ref_planes', 'Reference Planes', 'Select 2 planes to measure the stack-up effect from.')
    selection_input.addSelectionFilter('PlanarFaces')
    selection_input.addSelectionFilter('ConstructionPlanes')
    selection_input.setSelectionLimits(2, 2) 

    # Add buttons
    button_row = t1.addButtonRowCommandInput('dim_type', 'Dimension Type', False)
    button_row.listItems.add('Linear', False, ic.lin_icon)
    button_row.listItems.add('Angular', False, ic.ang_icon)

    t1.addIntegerSpinnerCommandInput("tab_manager", "Num. Components", 1, 5, 1, 1)

    # Pre-create all possible tabs
    for i in range(5):
        id = f"component_{i}"
        tab = Tab(f"Comp. {i+1}", id, inputs)
        tab.object.isVisible = (i == 0)  # Show only the first by default
        tabs.append(tab)

    # Hook up handlers
    futil.add_handler(args.command.inputChanged, command_input_changed, local_handlers=local_handlers)
    futil.add_handler(args.command.execute, command_execute, local_handlers=local_handlers)
    futil.add_handler(args.command.executePreview, command_preview, local_handlers=local_handlers)
    futil.add_handler(args.command.validateInputs, command_validate_input, local_handlers=local_handlers)
    futil.add_handler(args.command.destroy, command_destroy, local_handlers=local_handlers)


def pointsOnPlane(ref, n: int):
    plane = ref.selection(n).entity.geometry
    origin = plane.origin
    normal = plane.normal
    u_dir = plane.uDirection

    # Create 3 points in the plane
    pt1 = origin
    pt2 = origin.copy()
    pt2.translateBy(u_dir)

    # Create a third point by crossing to vDirection
    v_dir = plane.normal.crossProduct(u_dir)
    pt3 = origin.copy()
    pt3.translateBy(v_dir)

    return [pt1.asArray(), pt2.asArray(), pt3.asArray()]


# This event handler is called when the user clicks the OK button in the command dialog or 
# is immediately called after the created event not command inputs were created for the dialog.
def command_execute(args: adsk.core.CommandEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Command Execute Event')

    # TODO ******************************** Your code here ********************************

    # Get a reference to your command's inputs.
    inputs = args.command.commandInputs

    ref_planes = inputs.itemById('ref_planes')
    dim_type = inputs.itemById('dim_type')    
    tab_manager = inputs.itemById('tab_manager')

    n_tabs=adsk.core.IntegerSpinnerCommandInput.cast(tab_manager).value

    data = {
        "main_plane": [],
        "ref_plane": [],
        "metric_type": "",
        "components": []
    }

    futil.log(f"main plane vertices:")
    # futil.log(f"{ref_planes.selection(0).entity.vertices.item(0).geometry.asArray()}")
    # futil.log(f"{ref_planes.selection(0).entity.vertices.item(1).geometry.asArray()}")
    # futil.log(f"{ref_planes.selection(0).entity.vertices.item(2).geometry.asArray()}")

    arr = []

    # arr.append(ref_planes.selection(0).entity.vertices.item(0).geometry.asArray())
    # arr.append(ref_planes.selection(0).entity.vertices.item(1).geometry.asArray())
    # arr.append(ref_planes.selection(0).entity.vertices.item(2).geometry.asArray())

    #data['main_plane'] = arr
    data['main_plane'] = pointsOnPlane(ref_planes, 0)

    futil.log("\nref plane vertices:")
    futil.log(f"{ref_planes.selection(1).entity.vertices.item(0).geometry.asArray()}")
    futil.log(f"{ref_planes.selection(1).entity.vertices.item(1).geometry.asArray()}")
    futil.log(f"{ref_planes.selection(1).entity.vertices.item(2).geometry.asArray()}")

    arr = []

    arr.append(ref_planes.selection(1).entity.vertices.item(0).geometry.asArray())
    arr.append(ref_planes.selection(1).entity.vertices.item(1).geometry.asArray())
    arr.append(ref_planes.selection(1).entity.vertices.item(2).geometry.asArray())

    data['ref_plane'] = arr

    futil.log("\nmeasurement type:")
    futil.log(f"{adsk.core.ButtonRowCommandInput.cast(dim_type).selectedItem.name}")
    data['metric_type'] = adsk.core.ButtonRowCommandInput.cast(dim_type).selectedItem.name

    futil.log("\n number of components:")
    futil.log(f"{n_tabs}")

    # TODO - make a data object for tolerances and for components - then populate for each run in the loop and that should take care of all the JSOn formatting DONE!
    # After that, work on integration/parsing with python script, then maybe work on some more tolerance types and more specific datum definitions? IP
    # then finally try to package it together (ie publish package straight to pip, figure out a way to run it all here - maybe flask is a potential candidate but i dont wanna do that...)

    components = []
    for i in range(n_tabs):
        component={
            "name": "",
            "plane": [],
            "axis": [],
            "tolerances": []
        }
        n=tabs[i]
        name = inputs.itemById('text_box_'+n.id).text
        vertices = n.pts
        axes = n.axs
        futil.log(f"Component: {name}")
        component['name'] = name

        futil.log("vertices:")
        arr = []

        arr.append(vertices.selection(0).entity.geometry.asArray())
        arr.append(vertices.selection(1).entity.geometry.asArray())
        arr.append(vertices.selection(2).entity.geometry.asArray())

        component['plane'] = arr

        futil.log(f"{vertices.selection(0).entity.geometry.asArray()}")
        futil.log(f"{vertices.selection(1).entity.geometry.asArray()}")
        futil.log(f"{vertices.selection(2).entity.geometry.asArray()}")

        arr = []

        arr.append(axes.selection(0).entity.geometry.direction.asArray())
        arr.append(axes.selection(1).entity.geometry.direction.asArray())
        arr.append(axes.selection(2).entity.geometry.direction.asArray())

        component['axis'] = arr

        futil.log("\naxes: ")
        futil.log(f"{axes.selection(0).entity.geometry.direction.asArray()}")
        futil.log(f"{axes.selection(1).entity.geometry.direction.asArray()}")
        futil.log(f"{axes.selection(2).entity.geometry.direction.asArray()}")

        futil.log(f"\nnumber of tolerances: {n.spinner.value}")

        tolerances = []
        for j in range(n.spinner.value):
            tolerance= {
                            "type": "",
                            "tol": [],
                        }
            tol=[]
            for k in range(3):
                item = n.sectionInputs.item((k+2)+(4*j))
                if(item.classType() == adsk.core.DropDownCommandInput.classType()):
                    futil.log(f"Tolerance type: {item.selectedItem.name}")
                    tolerance['type'] = item.selectedItem.name
                elif(item.classType() == adsk.core.ValueCommandInput.classType()):
                    futil.log(f"tolerance: {item.value*10}")
                    tol.append(item.value*10)
            tolerance['tol'] = sorted(tol)
            tolerances.append(tolerance)
        
        component['tolerances'] = tolerances
        components.append(component)
    
    data['components'] = components

    save_json_safe(data)



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
        for n in tabs:
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
        for i, tab in enumerate(tabs):
            tab.setEnabled(i < value)  # Show and enable first N tabs only

    elif changed_input.id == 'axes_component_0':
        futil.log(f"{changed_input.selection(0).entity.geometry.direction.asArray()}")

def command_validate_input(args: adsk.core.ValidateInputsEventArgs):
    # Only validate inputs from the main tab (tab_main)
    inputs = args.inputs
    tab_main = inputs.itemById('tab_main')
    args.areInputsValid = True
        

# This event handler is called when the command terminates.
def command_destroy(args: adsk.core.CommandEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Command Destroy Event')

    for n in tabs:
        n.kill_tab()

    global local_handlers
    local_handlers = []


def p(msg):
    ui.messageBox(msg)

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

        #label
        text_box_message = f"<b>Tolerance {int(0)+1}</b>"
        text_box_input = self.sectionInputs.addTextBoxCommandInput('text_box_input_0'+id, 'Text Box', text_box_message, 1, True)
        text_box_input.isFullWidth = True

        # Add dropdown
        dropdown = self.sectionInputs.addDropDownCommandInput('dropdown_0'+id, 'Tol. Type', adsk.core.DropDownStyles.LabeledIconDropDownStyle)
        dropdown.listItems.add('Perpendicular', True, ic.perp_icon)
        dropdown.listItems.add('Concentric', False, ic.conc_icon)

        # Add value inputs
        default_unit = app.activeProduct.unitsManager.defaultLengthUnits
        self.sectionInputs.addValueInput('upper_tol_'+id+self.id, 'Upper Tol.', default_unit, adsk.core.ValueInput.createByString('0.1'))
        self.sectionInputs.addValueInput('lower_tol_'+id+self.id, 'Lower Tol.', default_unit, adsk.core.ValueInput.createByString('-0.1'))


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

        # create new ones with range depending on total number
        for i in range(len(tr), value):
            id = str(i)

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


def save_json_safe(data, filename='my_data.json'):
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        # Get user's Documents folder
        documents_path = os.path.expanduser('~/Documents')
        folder_path = os.path.join(documents_path, 'Fusion360Exports')

        # Create folder if it doesn't exist
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        file_path = os.path.join(folder_path, filename)

        # Save the data as JSON
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)

        ui.messageBox(f'Successfully saved JSON to:\n{file_path}')
        return file_path

    except Exception as e:
        if ui:
            ui.messageBox(f'Error saving JSON file:\n{e}')
        else:
            print(f'Error: {e}')