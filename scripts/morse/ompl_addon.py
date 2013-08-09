# ompl_addon.py
# To be installed as a Blender addon

bl_info = {
    "name":"OMPL Interface",
    "category":"Game Engine",
    "description":"Planning with OMPL (requires MORSE)",
    "location":"Game > OMPL",
    "author":"Caleb Voss"
}

import configparser
import os
import socket
import subprocess
import sys
import time

import bpy
import mathutils

# the following path is in sys.path when you start python3 normally, but not when in Blender?!?
sys.path.append('/usr/local/lib/python3.2/dist-packages')
import morse.builder


OMPL_DIR='/home/caleb/repos/ompl_morse/scripts/morse'
sys.path.append(OMPL_DIR)
import environment

inf = float('inf')

# Addon operators

class Plan(bpy.types.Operator):
    """Invoke OMPL Planning"""
    bl_idname = "ompl.plan"
    bl_label = "Plan..."
    
    # automatically set by the Blender file selector dialog
    filepath = bpy.props.StringProperty(subtype="FILE_PATH")
    
    def execute(self, context):
        """
        Called when the dialogs finish.
        """
        
        print('Starting planner...')
        print("Planning on %s, saving to %s" % (bpy.data.filepath, self.filepath))
        subprocess.Popen(['morse', '-c', 'run', OMPL_DIR+'/builder.py', '--', bpy.data.filepath, self.filepath, 'PLAN'])
        # for the newer MORSE interface, use this instead of the above line:
        #subprocess.Popen(['morse', '-c', 'run', 'ompl', 'OMPL_DIR+'/builder.py', '--', bpy.data.filepath, self.filepath, 'PLAN'])
        
        return {'FINISHED'}

    def invoke(self, context, event):
        """
        Called when the button is pressed.
        """
        
        if not context.scene.objects.get('__settings'):
            # Bounds Configuration hasn't been setup for this file yet
            bpy.ops.ompl.boundsconfig('INVOKE_DEFAULT')
        
        bpy.ops.wm.save_mainfile()
        
        # File selector for the path file
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class Play(bpy.types.Operator):
    """Invoke OMPL Playback"""
    bl_idname = "ompl.play"
    bl_label = "Play..."
    
    # automatically set by the Blender file selector dialog
    filepath = bpy.props.StringProperty(subtype="FILE_PATH")
    
    def execute(self, context):
        """
        Called when the dialogs finish.
        """
        
        print('Starting player...')
        print("Playing %s with %s" % (bpy.data.filepath, self.filepath))
        subprocess.Popen(['morse', '-c', 'run', OMPL_DIR+'/builder.py', '--', bpy.data.filepath, self.filepath, 'PLAY'])
        # for the newer MORSE interface, use this instead of the above line:
        #subprocess.Popen(['morse', '-c', 'run', 'ompl', 'OMPL_DIR+'/builder.py', '--', bpy.data.filepath, self.filepath, 'PLAY'])
        
        return {'FINISHED'}

    def invoke(self, context, event):
        """
        Called when the button is pressed.
        """
        
        # File selector for the path file
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

# Helpers for AddRobot class

def getRobots():
    """
    Compile list of valid MORSE robots.
    """
    excluded_robots = []    #TODO
    robotEnum = []
    i=0
    for cname in dir(morse.builder.robots):
        c = getattr(morse.builder.robots, cname)
        # is c a class?
        if isinstance(c, type):
            # does it inherit from Robot and is it neither Robot nor WheeledRobot?
            if issubclass(c, morse.builder.Robot) and c != morse.builder.Robot and c != morse.builder.WheeledRobot:
                # is is not in our exlusions list?
                if cname not in excluded_robots:
                    robotEnum.append((cname,cname,'morse.builder.robots.'+cname,i))
                    i += 1
    robotEnum.reverse()
    return robotEnum

def getControllers():
    """
    Compile list of controllers valid for the selected robot.
    """
    # exclude controllers that have non-numeric parameters, don't have a socket interface, or are irrelevant
    excluded_controllers = ['Armature','Destination','ForceTorque','Gripper','Keyboard','KukaLWR',
        'Light','Mocap','MocapControl','MotionXYW','Orientation','PTU','RotorcraftAttitude','SteerForce']
    controllerEnum = []
    i=0
    for cname in dir(morse.builder.actuators):
        c = getattr(morse.builder.actuators, cname)
        # is c a class?
        if isinstance(c, type):
            # does it inherit from Actuator and is it not Actuator?
            # OR does it inherit from ActuatorCreator and is it not ActuatorCreator?
            if (issubclass(c, morse.builder.Actuator) and
                c != morse.builder.Actuator) or \
                (issubclass(c, morse.builder.creator.ActuatorCreator) and
                c != morse.builder.creator.ActuatorCreator):
                # is it not in our exclusions list?
                if cname not in excluded_controllers:
                    controllerEnum.append((cname,cname,'morse.builder.actuators.'+cname,i))
                    i += 1
    controllerEnum.reverse()
    return controllerEnum
        
class AddRobot(bpy.types.Operator):
    """Add a MORSE Robot to the Scene"""
    bl_idname = "ompl.addrobot"
    bl_label = "Add Robot..."
    
    # automatically set by the Blender properties dialog
    robotEnum = getRobots()
    controllerEnum = getControllers()
    robot_type = bpy.props.EnumProperty(items=robotEnum, name="MORSE robot", default=robotEnum[-1][0])
    controller_type = bpy.props.EnumProperty(items=controllerEnum,
        name="MORSE actuator", default=controllerEnum[-1][0])
    
    def execute(self, context):
        """
        Called when this operator is run.
        """
        
        # add model for robot_type
        robot = getattr(morse.builder, self.robot_type)()
        robotObj = bpy.context.object
        
        # join all it's children
        bpy.ops.object.select_all(action='DESELECT')
        for child in robotObj.children:
            bpy.ops.object.select_pattern(pattern=child.name, case_sensitive=True)
        bpy.ops.object.select_pattern(pattern=robotObj.name, case_sensitive=True)
        bpy.ops.object.join()
        
        # make visible in a render
        robotObj.hide_render = False
        
        # remove unnecessary game properties
        while len(robotObj.game.properties) > 0:
            bpy.ops.object.game_property_remove()
        
        # add game properties for robot_type and controller_type
        bpy.ops.object.game_property_new(type='STRING', name="RobotType")
        bpy.context.object.game.properties['RobotType'].value = self.robot_type
        bpy.ops.object.game_property_new(type='STRING', name="ControllerType")
        bpy.context.object.game.properties['ControllerType'].value = self.controller_type
        
        
        return {'FINISHED'}

    def invoke(self, context, event):
        """
        Called when the button is pressed.
        """
        
        # choose robot and controller
        return bpy.context.window_manager.invoke_props_dialog(self)
    
        

class BoundsConfiguration(bpy.types.Operator):
    """Configure the state and control bounds"""
    bl_idname = "ompl.boundsconfig"
    bl_label = "Bounds Configuration..."
    
    # Properties displayed in the dialog
    autopb = bpy.props.BoolProperty(name="Automatic position bounds",
        description="Overrides user-provided numbers by analyzing the scene",
        default=True)
    pbx = bpy.props.FloatProperty(name="Min", default=-1000, min=-1000, max=1000)
    pbX = bpy.props.FloatProperty(name="Max", default=1000, min=-1000, max=1000)
    pby = bpy.props.FloatProperty(name="Min", default=-1000, min=-1000, max=1000)
    pbY = bpy.props.FloatProperty(name="Max", default=1000, min=-1000, max=1000)
    pbz = bpy.props.FloatProperty(name="Min", default=-1000, min=-1000, max=1000)
    pbZ = bpy.props.FloatProperty(name="Max", default=1000, min=-1000, max=1000)
    lbm = bpy.props.FloatProperty(name="Min", default=-1000, min=-1000, max=1000)
    lbM = bpy.props.FloatProperty(name="Max", default=1000, min=-1000, max=1000)
    abm = bpy.props.FloatProperty(name="Min", default=-1000, min=-1000, max=1000)
    abM = bpy.props.FloatProperty(name="Max", default=1000, min=-1000, max=1000)
    cbm0 = bpy.props.FloatProperty(name="Min", default=-10, min=-1000, max=1000)
    cbM0 = bpy.props.FloatProperty(name="Max", default=10, min=-1000, max=1000)
    cbm1 = bpy.props.FloatProperty(name="Min", default=-10, min=-1000, max=1000)
    cbM1 = bpy.props.FloatProperty(name="Max", default=10, min=-1000, max=1000)
    cbm2 = bpy.props.FloatProperty(name="Min", default=-10, min=-1000, max=1000)
    cbM2 = bpy.props.FloatProperty(name="Max", default=10, min=-1000, max=1000)
    cbm3 = bpy.props.FloatProperty(name="Min", default=-10, min=-1000, max=1000)
    cbM3 = bpy.props.FloatProperty(name="Max", default=10, min=-1000, max=1000)
    cbm4 = bpy.props.FloatProperty(name="Min", default=-10, min=-1000, max=1000)
    cbM4 = bpy.props.FloatProperty(name="Max", default=10, min=-1000, max=1000)
    cbm5 = bpy.props.FloatProperty(name="Min", default=-10, min=-1000, max=1000)
    cbM5 = bpy.props.FloatProperty(name="Max", default=10, min=-1000, max=1000)
    cbm6 = bpy.props.FloatProperty(name="Min", default=-10, min=-1000, max=1000)
    cbM6 = bpy.props.FloatProperty(name="Max", default=10, min=-1000, max=1000)
    cbm7 = bpy.props.FloatProperty(name="Min", default=-10, min=-1000, max=1000)
    cbM7 = bpy.props.FloatProperty(name="Max", default=10, min=-1000, max=1000)
    cbm8 = bpy.props.FloatProperty(name="Min", default=-10, min=-1000, max=1000)
    cbM8 = bpy.props.FloatProperty(name="Max", default=10, min=-1000, max=1000)
    cbm9 = bpy.props.FloatProperty(name="Min", default=-10, min=-1000, max=1000)
    cbM9 = bpy.props.FloatProperty(name="Max", default=10, min=-1000, max=1000)
    cbm10 = bpy.props.FloatProperty(name="Min", default=-10, min=-1000, max=1000)
    cbM10 = bpy.props.FloatProperty(name="Max", default=10, min=-1000, max=1000)
    cbm11 = bpy.props.FloatProperty(name="Min", default=-10, min=-1000, max=1000)
    cbM11 = bpy.props.FloatProperty(name="Max", default=10, min=-1000, max=1000)
    cbm12 = bpy.props.FloatProperty(name="Min", default=-10, min=-1000, max=1000)
    cbM12 = bpy.props.FloatProperty(name="Max", default=10, min=-1000, max=1000)
    cbm13 = bpy.props.FloatProperty(name="Min", default=-10, min=-1000, max=1000)
    cbM13 = bpy.props.FloatProperty(name="Max", default=10, min=-1000, max=1000)
    cbm14 = bpy.props.FloatProperty(name="Min", default=-10, min=-1000, max=1000)
    cbM14 = bpy.props.FloatProperty(name="Max", default=10, min=-1000, max=1000)
    cbm15 = bpy.props.FloatProperty(name="Min", default=-10, min=-1000, max=1000)
    cbM15 = bpy.props.FloatProperty(name="Max", default=10, min=-1000, max=1000)

    
    def execute(self, context):
        """
        Called when this operator is run.
        """
        
        # Save settings to file
        settings = context.scene.objects['__settings'].game.properties
        settings['autopb'].value = self.autopb
        settings['pbx'].value = self.pbx
        settings['pbX'].value = self.pbX
        settings['pby'].value = self.pby
        settings['pbY'].value = self.pbY
        settings['pbz'].value = self.pbz
        settings['pbZ'].value = self.pbZ
        settings['lbm'].value = self.lbm
        settings['lbM'].value = self.lbM
        settings['abm'].value = self.abm
        settings['abM'].value = self.abM
        for i in range(16):
            settings['cbm%i'%i].value = getattr(self, 'cbm%i'%i)
            settings['cbM%i'%i].value = getattr(self, 'cbM%i'%i)
        
        # Allow dialog defaults to be changed by resetting the properties
        del BoundsConfiguration.autopb, BoundsConfiguration.pbx, BoundsConfiguration.pbX,\
            BoundsConfiguration.pby, BoundsConfiguration.pbY, BoundsConfiguration.pbz,\
            BoundsConfiguration.pbZ, BoundsConfiguration.lbm, BoundsConfiguration.lbM,\
            BoundsConfiguration.abm, BoundsConfiguration.abM
        for i in range(16):
            delattr(BoundsConfiguration, 'cbm%i'%i)
            delattr(BoundsConfiguration, 'cbM%i'%i)
        
        BoundsConfiguration.autopb = bpy.props.BoolProperty(name="Automatic position bounds",
            description="Overrides user-provided numbers by analyzing the scene",
            default=settings['autopb'].value)
        BoundsConfiguration.pbx = bpy.props.FloatProperty(name="Min", default=settings['pbx'].value,min=-1000, max=1000)
        BoundsConfiguration.pbX = bpy.props.FloatProperty(name="Max", default=settings['pbX'].value, min=-1000, max=1000)
        BoundsConfiguration.pby = bpy.props.FloatProperty(name="Min", default=settings['pby'].value, min=-1000, max=1000)
        BoundsConfiguration.pbY = bpy.props.FloatProperty(name="Max", default=settings['pbY'].value, min=-1000, max=1000)
        BoundsConfiguration.pbz = bpy.props.FloatProperty(name="Min", default=settings['pbz'].value, min=-1000, max=1000)
        BoundsConfiguration.pbZ = bpy.props.FloatProperty(name="Max", default=settings['pbZ'].value, min=-1000, max=1000)
        BoundsConfiguration.lbm = bpy.props.FloatProperty(name="Min", default=settings['lbm'].value, min=-1000, max=1000)
        BoundsConfiguration.lbM = bpy.props.FloatProperty(name="Max", default=settings['lbM'].value, min=-1000, max=1000)
        BoundsConfiguration.abm = bpy.props.FloatProperty(name="Min", default=settings['abm'].value, min=-1000, max=1000)
        BoundsConfiguration.abM = bpy.props.FloatProperty(name="Max", default=settings['abM'].value, min=-1000, max=1000)
        for i in range(16):
            setattr(BoundsConfiguration, 'cbm%i'%i, bpy.props.FloatProperty(name="Min", default=settings['cbm%i'%i].value, min=-1000, max=1000))
            setattr(BoundsConfiguration, 'cbM%i'%i, bpy.props.FloatProperty(name="Max", default=settings['cbM%i'%i].value, min=-1000, max=1000))
        """        
        BoundsConfiguration.cbm0 = bpy.props.FloatProperty(name="Min", default=settings['cbm0'].value, min=-1000, max=1000)
        BoundsConfiguration.cbM0 = bpy.props.FloatProperty(name="Max", default=settings['cbM0'].value, min=-1000, max=1000)
        BoundsConfiguration.cbm1 = bpy.props.FloatProperty(name="Min", default=settings['cbm1'].value, min=-1000, max=1000)
        BoundsConfiguration.cbM1 = bpy.props.FloatProperty(name="Max", default=settings['cbM1'].value, min=-1000, max=1000)
        BoundsConfiguration.cbm2 = bpy.props.FloatProperty(name="Min", default=settings['cbm2'].value, min=-1000, max=1000)
        BoundsConfiguration.cbM2 = bpy.props.FloatProperty(name="Max", default=settings['cbM2'].value, min=-1000, max=1000)
        BoundsConfiguration.cbm3 = bpy.props.FloatProperty(name="Min", default=settings['cbm3'].value, min=-1000, max=1000)
        BoundsConfiguration.cbM3 = bpy.props.FloatProperty(name="Max", default=settings['cbM3'].value, min=-1000, max=1000)
        BoundsConfiguration.cbm4 = bpy.props.FloatProperty(name="Min", default=settings['cbm4'].value, min=-1000, max=1000)
        BoundsConfiguration.cbM4 = bpy.props.FloatProperty(name="Max", default=settings['cbM4'].value, min=-1000, max=1000)
        BoundsConfiguration.cbm5 = bpy.props.FloatProperty(name="Min", default=settings['cbm5'].value, min=-1000, max=1000)
        BoundsConfiguration.cbM5 = bpy.props.FloatProperty(name="Max", default=settings['cbM5'].value, min=-1000, max=1000)
        BoundsConfiguration.cbm6 = bpy.props.FloatProperty(name="Min", default=settings['cbm6'].value, min=-1000, max=1000)
        BoundsConfiguration.cbM6 = bpy.props.FloatProperty(name="Max", default=settings['cbM6'].value, min=-1000, max=1000)
        BoundsConfiguration.cbm7 = bpy.props.FloatProperty(name="Min", default=settings['cbm7'].value, min=-1000, max=1000)
        BoundsConfiguration.cbM7 = bpy.props.FloatProperty(name="Max", default=settings['cbM7'].value, min=-1000, max=1000)
        BoundsConfiguration.cbm8 = bpy.props.FloatProperty(name="Min", default=settings['cbm8'].value, min=-1000, max=1000)
        BoundsConfiguration.cbM8 = bpy.props.FloatProperty(name="Max", default=settings['cbM8'].value, min=-1000, max=1000)
        BoundsConfiguration.cbm9 = bpy.props.FloatProperty(name="Min", default=settings['cbm9'].value, min=-1000, max=1000)
        BoundsConfiguration.cbM9 = bpy.props.FloatProperty(name="Max", default=settings['cbM9'].value, min=-1000, max=1000)
        BoundsConfiguration.cbm10 = bpy.props.FloatProperty(name="Min", default=settings['cbm10'].value, min=-1000, max=1000)
        BoundsConfiguration.cbM10 = bpy.props.FloatProperty(name="Max", default=settings['cbM10'].value, min=-1000, max=1000)
        BoundsConfiguration.cbm11 = bpy.props.FloatProperty(name="Min", default=settings['cbm11'].value, min=-1000, max=1000)
        BoundsConfiguration.cbM11 = bpy.props.FloatProperty(name="Max", default=settings['cbM11'].value, min=-1000, max=1000)
        BoundsConfiguration.cbm12 = bpy.props.FloatProperty(name="Min", default=settings['cbm12'].value, min=-1000, max=1000)
        BoundsConfiguration.cbM12 = bpy.props.FloatProperty(name="Max", default=settings['cbM12'].value, min=-1000, max=1000)
        BoundsConfiguration.cbm13 = bpy.props.FloatProperty(name="Min", default=settings['cbm13'].value, min=-1000, max=1000)
        BoundsConfiguration.cbM13 = bpy.props.FloatProperty(name="Max", default=settings['cbM13'].value, min=-1000, max=1000)
        BoundsConfiguration.cbm14 = bpy.props.FloatProperty(name="Min", default=settings['cbm14'].value, min=-1000, max=1000)
        BoundsConfiguration.cbM14 = bpy.props.FloatProperty(name="Max", default=settings['cbM14'].value, min=-1000, max=1000)
        BoundsConfiguration.cbm15 = bpy.props.FloatProperty(name="Min", default=settings['cbm15'].value, min=-1000, max=1000)
        BoundsConfiguration.cbM15 = bpy.props.FloatProperty(name="Max", default=settings['cbM15'].value, min=-1000, max=1000)
        """
        bpy.utils.unregister_class(BoundsConfiguration)
        bpy.utils.register_class(BoundsConfiguration)
        
        return {'FINISHED'}

    def invoke(self, context, event):
        """
        Called when the button is pressed.
        """
        
        # If the settings have not been set before
        if not context.scene.objects.get('__settings'):
            bpy.ops.object.add()
            settings = bpy.context.object
            settings.name = '__settings'
            props = settings.game.properties
            bpy.ops.object.game_property_new(type='BOOL', name='autopb')
            props['autopb'].value = True
            bpy.ops.object.game_property_new(type='FLOAT', name='pbx')
            props['pbx'].value = -1000
            bpy.ops.object.game_property_new(type='FLOAT', name='pbX')
            props['pbX'].value = 1000
            bpy.ops.object.game_property_new(type='FLOAT', name='pby')
            props['pby'].value = -1000
            bpy.ops.object.game_property_new(type='FLOAT', name='pbY')
            props['pbY'].value = 1000
            bpy.ops.object.game_property_new(type='FLOAT', name='pbz')
            props['pbz'].value = -1000
            bpy.ops.object.game_property_new(type='FLOAT', name='pbZ')
            props['pbZ'].value = 1000
            bpy.ops.object.game_property_new(type='FLOAT', name='lbm')
            props['lbm'].value = -1000
            bpy.ops.object.game_property_new(type='FLOAT', name='lbM')
            props['lbM'].value = 1000
            bpy.ops.object.game_property_new(type='FLOAT', name='abm')
            props['abm'].value = -1000
            bpy.ops.object.game_property_new(type='FLOAT', name='abM')
            props['abM'].value = 1000
            for i in range(16):
                bpy.ops.object.game_property_new(type='FLOAT', name='cbm%i'%i)
                props['cbm%i'%i].value = -10
                bpy.ops.object.game_property_new(type='FLOAT', name='cbM%i'%i)
                props['cbM%i'%i].value = 10
        
        # Query MORSE for cdesc by starting it up temporarily (clunky, but it needs to be done)
        print('Starting query...')
        subprocess.Popen(['morse', '-c', 'run', OMPL_DIR+'/builder.py', '--', bpy.data.filepath, ".", 'QUERY'],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        while True:
            try:
                sockS = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sockC = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sockS.connect(('localhost', 50007))
                sockC.connect(('localhost', 4000))
            except:
                time.sleep(1)
                continue
            break
        self.cdesc = environment.MyEnvironment(sockS, sockC, True).cdesc
        
        # Set bounds dialog
        return bpy.context.window_manager.invoke_props_dialog(self, width=1100)
    
        
    def draw(self, context):
        """
        Defines how the popup should look.
        """
        
        mainlayout = self.layout.row()
        # 3 sections in first column:
        sections = mainlayout.column()
        sections.label(text="Position Bounds:")
        sections.prop(self, 'autopb')
        pb = sections.row()
        sections.separator()
        sections.label(text="Linear Velocity Bounds:")
        lb = sections.row()
        sections.separator()
        sections.label(text="Angular Velocity Bounds:")
        ab = sections.row()
        # 1 section in second column
        cb = mainlayout.column()
        cb.label(text="Control Input Bounds:")
        cbrow1 = cb.row()
        cbrow2 = cb.row()
        cbrow3 = cb.row()
        cbrow4 = cb.row()
        
        # In positional bounds sections, make 3 columns for X,Y,Z, with Min,Max in each
        X = pb.column()
        X.label(text="X")
        X.prop(self, 'pbx', text="Min")
        X.prop(self, 'pbX', text="Max")
        Y = pb.column()
        Y.label(text="Y")
        Y.prop(self, 'pby', text="Min")
        Y.prop(self, 'pbY', text="Max")
        Z = pb.column()
        Z.label(text="Z")
        Z.prop(self, 'pbz', text="Min")
        Z.prop(self, 'pbZ', text="Max")
        
        # Linear velocity bounds Min,Max
        lb.prop(self, 'lbm', text="Min")
        lb.prop(self, 'lbM', text="Max")
        
        # Angular " "
        ab.prop(self, 'abm', text="Min")
        ab.prop(self, 'abM', text="Max")
        
        # Control Input " "
        last_component = None
        i = 0
        k = 0
        cbrow = [cbrow1, cbrow2, cbrow3, cbrow4]
        for control in self.cdesc[2:]:
            if control[0] != last_component:
                robot = cbrow[int(k/4)].column()   # only allow 4 robots per row
                k += 1
                # print the component name
                robot.label(text="robot_"+control[0][7:]+":")
                services = robot.box()
            # print the controller name
            services.label(text=control[1]+":")
            args = services.row()
            for j in range(control[2]):
                # print the argument number
                con = args.column()
                con.label(text="Arg %i"%j)
                con.prop(self, 'cbm%i'%i, text="Min")
                con.prop(self, 'cbM%i'%i, text="Max")
                i += 1

# Menus

class OMPLMenu(bpy.types.Menu):
    bl_idname = "INFO_MT_game_ompl"
    bl_label = "OMPL"
    
    def draw(self, context):
        self.layout.operator_context = 'INVOKE_DEFAULT'
        self.layout.operator(Plan.bl_idname)
        self.layout.operator(Play.bl_idname)
        self.layout.operator(AddRobot.bl_idname)
        self.layout.operator(BoundsConfiguration.bl_idname)


def menu_func(self, context):
    self.layout.menu(OMPLMenu.bl_idname)

# Addon enable/disable functions

def register():
    """
    Called when this addon is enabled or Blender starts.
    """
    
    # uncomment for the latest MORSE interface
    """
    # Ensure that MORSE environment 'ompl' is registered in ~/.morse/config
    config_path = os.path.expanduser("~/.morse")
    if not os.path.exists(config_path):
        os.mkdir(config_path)
    config_file = os.path.join(config_path, "config")

    conf = configparser.SafeConfigParser()
    conf.read(config_file)
    if not conf.has_section("sites"):
        conf.add_section("sites")
    conf.set('sites', 'ompl', OMPL_DIR)

    with open(config_file, 'w') as configfile:
        conf.write(configfile)
    """
    
    # Set up menus
    bpy.utils.register_class(Plan)
    bpy.utils.register_class(Play)
    bpy.utils.register_class(AddRobot)
    bpy.utils.register_class(BoundsConfiguration)
    bpy.utils.register_class(OMPLMenu)
    bpy.types.INFO_MT_game.prepend(menu_func)

def unregister():
    """
    Called when this addon is disabled.
    """
    bpy.utils.unregister_class(Plan)
    bpy.utils.unregister_class(Play)
    bpy.utils.unregister_class(AddRobot)
    bpy.utils.unregister_class(BoundsConfiguration)
    bpy.utils.unregister_class(OMPLMenu)
    bpy.types.INFO_MT_game.remove(menu_func)




