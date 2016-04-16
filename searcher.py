#!/usr/bin/env python3


import json
import time
import subprocess
import threading
from gi.repository import Gtk, Gdk, GLib


class AsThread:
    """AsThread
    A hacky threading decorator. When placed above a function itl
    force the function to be run in a new "thread" whenver it is called.
    """
    def __init__(self, daemon=True):
        self.daemon = daemon

    def __call__(self, function):
        def run(*args, **kwargs):
            thread = threading.Thread(target=function, args=args,
                                      kwargs=kwargs)
            thread.daemon = self.daemon
            thread.start()
            return None
        return run


def idle_call(function):
    """idle_call
    This decorator prevents 2 threads accessing the same Gtk resource at
    the same time. If the resource is being used it will wait until
    it is no longer in use, then do its stuff.
    Without this, the program would crash lots. Thanks threading!
    """
    def run(*args, **kwargs):
        GLib.idle_add(function, *args, **kwargs)
        return None
    return run


class SkillList(Gtk.ScrolledWindow):
    """SkillList
    A list of skills for the user to select from.
    There is a checkbox next to each skill if the user
    selects it the program will attempt to find it when you click search
    """

    def __init__(self):
        Gtk.ScrolledWindow.__init__(self)
        self.list = Gtk.ListStore(str, bool, str)
        self.view = Gtk.TreeView(self.list)
        self.view.set_activate_on_single_click(True)
        self.view.set_hexpand(True)
        self.view.set_vexpand(True)
        self.view.connect('row-activated', self.clicked)
        self.view.set_tooltip_column(2)
        check_render = Gtk.CellRendererToggle()
        check_render.set_padding(20, 15)
        text_renderer = Gtk.CellRendererText()
        text_renderer.set_padding(20, 15)
        text_column = Gtk.TreeViewColumn('Skills', text_renderer, text=0)
        check_column = Gtk.TreeViewColumn('', check_render, active=1)
        check_column.set_clickable(True)
        check_column.connect('clicked', self.check_column_clicked)
        self.view.append_column(text_column)
        self.view.append_column(check_column)
        self.add(self.view)
        self.populate()

    def populate(self):
        """populate
        Populates the skill list with all the skills and descriptions.
        """
        for skill_name in sorted(skills):
            self.list.append([skill_name, 0, '{} ({} {:+})'.format(skills[
                             skill_name]['Description'],
                             skills[skill_name]['Jewel'],
                             skills[skill_name]['Points'])])
        return None

    def clicked(self, view, path, column):
        """clicked
        Called when the user clicks a row, it will toggle the checkbox.
        """
        index = int(path.to_string())
        self.list[index][1] = not self.list[index][1]
        return None

    def check_column_clicked(self, *params):
        for item in self.list:
            item[1] = 0
        return True


class SearchButton(Gtk.Button):
    """SearchButton
    The button that starts the searching!
    """

    def __init__(self):
        Gtk.Button.__init__(self)
        self.set_label('Search')
        self.connect('clicked', self.clicked)
        self.set_vexpand(True)
        self.set_hexpand(True)

    @idle_call
    def clicked(self, button):
        """clicked
        Called when the user clicks the button
        """
        # Obtain a reference to the MainWindow class and call its search()
        # method.
        main_window = self.get_parent().get_parent()
        main_window.search()
        return None

    @idle_call
    def disable(self):
        self.set_sensitive(False)
        return None

    @idle_call
    def enable(self):
        self.set_sensitive(True)
        return None


class ResultArea(Gtk.ScrolledWindow):
    """ResultArea
    A scrollable area for the results.
    """

    def __init__(self):
        Gtk.ScrolledWindow.__init__(self)
        self.set_vexpand(True)
        self.set_hexpand(True)
        self.items = Gtk.VBox()

        title = Gtk.Label()
        title.set_markup('<span foreground="#888" '
                         'size="x-large">Results</span>')
        title.set_justify(Gtk.Justification.LEFT)
        instruction = Gtk.Label()
        instruction.set_markup('<span size="x-large" foreground="#999">'
                               'Please choose one or more skills from the'
                               ' list on the left \nthen press search!'
                               '</span>')
        instruction.set_halign(Gtk.Align.CENTER)

        self.items.pack_start(title, 0, 1, 10)
        self.items.pack_start(instruction, True, True, 10)
        self.add(self.items)

    @AsThread()
    def clear(self):
        """clear
        Clears the result area and creates the default widgets
        """
        self.remove_items()
        return None

    @idle_call
    def remove_items(self):
        for item in self.items:
            self.items.remove(item)
        title = Gtk.Label()
        title.set_markup('<span foreground="#888" '
                         'size="x-large">Results</span>')
        title.set_justify(Gtk.Justification.LEFT)
        self.items.pack_start(title, 0, 1, 10)
        self.show_all()
        return None

    @idle_call
    def add_result(self, result):
        """add_result
        Adds a result to the result area.
        """
        self.items.pack_start(result, 0, 1, 10)
        self.show_all()
        return None

    @idle_call
    def add_end_of_results(self):
        end_of_results = Gtk.Label()
        end_of_results.set_markup('<span size="xx-large" foreground="#888">'
                                  'End of Results</span>')

        self.items.pack_start(end_of_results, True, True, 10)
        self.show_all()
        return None

    @idle_call
    def add_search_string(self, string):
        label = Gtk.Label(string)
        self.items.pack_start(label, True, True, 10)
        return None


class Result(Gtk.HBox):
    """Result
    A bunch of widgets for each result.
    """
    def __init__(self, index, armour_set):
        Gtk.HBox.__init__(self)
        self.armour_set = armour_set

        h_piece = armour_set['head']
        c_piece = armour_set['chest']
        a_piece = armour_set['arms']
        w_piece = armour_set['waist']
        l_piece = armour_set['legs']

        set_box = Gtk.VBox()

        title = Gtk.Label()
        title.set_halign(Gtk.Align.START)
        title.set_markup('<span size="xx-large" foreground="#999"><a '
                         'href="#">Result {}</a></span>'.format(index))
        title.connect('activate-link', self.clicked)

        set_box.pack_start(title, True, True, 20)

        set_title = Gtk.Label()
        set_title.set_markup('<span font-weight="bold">Armour Pieces:</span>')
        set_title.set_halign(Gtk.Align.START)

        head_name = Gtk.Label()
        head_name.set_markup('\t<span font-weight="bold">Head:</span> {'
                             '}'.format(h_piece))
        head_name.set_halign(Gtk.Align.START)
        head_name.set_tooltip_text(json.dumps(armour[h_piece], indent='\t'))

        chest_name = Gtk.Label()
        chest_name.set_markup('\t<span font-weight="bold">Chest:</span> {'
                              '}'.format(c_piece))
        chest_name.set_halign(Gtk.Align.START)
        chest_name.set_tooltip_text(json.dumps(armour[c_piece], indent='\t'))

        arms_name = Gtk.Label()
        arms_name.set_markup('\t<span font-weight="bold">Arms:</span> {'
                             '}'.format(a_piece))
        arms_name.set_halign(Gtk.Align.START)
        arms_name.set_tooltip_text(json.dumps(armour[a_piece], indent='\t'))

        waist_name = Gtk.Label()
        waist_name.set_markup('\t<span font-weight="bold">Waist:</span> {'
                              '}'.format(w_piece))
        waist_name.set_halign(Gtk.Align.START)
        waist_name.set_tooltip_text(json.dumps(armour[w_piece], indent='\t'))

        legs_name = Gtk.Label()
        legs_name.set_markup('\t<span font-weight="bold">Legs:</span> {'
                             '}'.format(l_piece))
        legs_name.set_halign(Gtk.Align.START)
        legs_name.set_tooltip_text(json.dumps(armour[l_piece], indent='\t'))

        defense_title = Gtk.Label()
        defense_title.set_markup('<span font-weight="bold">Defense:</span>')
        defense_title.set_halign(Gtk.Align.START)

        def_min = 0
        def_max = 0
        total_slots = 0

        for piece in armour_set:
            name = armour_set[piece]
            def_min += armour[name]['defense']['min']
            def_max += armour[name]['defense']['max']
            total_slots += armour[name]['slots']

        min_defense = Gtk.Label()
        min_defense.set_markup('\t<span font-weight="bold">Min:</span> {'
                               '}'.format(def_min))
        min_defense.set_halign(Gtk.Align.START)

        max_defense = Gtk.Label()
        max_defense.set_markup('\t<span font-weight="bold">Max:</span> {'
                               '}'.format(def_max))
        max_defense.set_halign(Gtk.Align.START)

        slots = Gtk.Label()
        slots.set_markup('<span font-weight="bold">Slots:</span> {}'.format(
                         total_slots))
        slots.set_halign(Gtk.Align.START)

        set_box.set_homogeneous(False)
        set_box.pack_start(set_title, True, True, 10)
        set_box.pack_start(head_name, True, True, 0)
        set_box.pack_start(chest_name, True, True, 0)
        set_box.pack_start(arms_name, True, True, 0)
        set_box.pack_start(waist_name, True, True, 0)
        set_box.pack_start(legs_name, True, True, 0)
        set_box.pack_start(defense_title, True, True, 10)
        set_box.pack_start(min_defense, True, True, 0)
        set_box.pack_start(max_defense, True, True, 0)
        set_box.pack_start(slots, True, True, 10)

        self.pack_start(set_box, 1, 1, 10)

        skill_points = {}
        for piece in armour_set:
            name = armour_set[piece]
            for skill in armour[name]['skills']:
                if skill not in skill_points:
                    skill_points[skill] = armour[name]['skills'][skill]
                else:
                    skill_points[skill] += armour[name]['skills'][skill]

        scroll = Gtk.ScrolledWindow()
        skill_list = Gtk.ListStore(str, int)
        skill_view = Gtk.TreeView(skill_list)
        text_render = Gtk.CellRendererText()
        name_column = Gtk.TreeViewColumn('Skill', text_render, text=0)
        point_column = Gtk.TreeViewColumn('Points', text_render, text=1)
        skill_view.append_column(name_column)
        skill_view.append_column(point_column)
        skill_view.set_vexpand(True)
        skill_view.set_hexpand(True)
        scroll.add(skill_view)

        for skill in sorted(skill_points, key=skill_points.get, reverse=True):
            skill_list.append([skill, skill_points[skill]])

        self.pack_start(scroll, True, True, 10)

    def clicked(self, *params):
        """clicked
        Generates a simple output of the selected output and copies
        it to your clipboard.
        """
        max_defense = 0
        min_defense = 0
        skill_points = {}
        res_points = {}
        slots = 0
        output = ''
        for piece in self.armour_set:
            name = self.armour_set[piece]
            slots += armour[name]['slots']
            for skill in armour[name]['skills']:
                if skill not in skill_points:
                    skill_points[skill] = armour[name]['skills'][skill]
                else:
                    skill_points[skill] += armour[name]['skills'][skill]
            for res in armour[name]['resistance']:
                if res not in res_points:
                    res_points[res] = armour[name]['resistance'][res]
                else:
                    res_points[res] += armour[name]['resistance'][res]
            max_defense += armour[name]['defense']['max']
            min_defense += armour[name]['defense']['min']
        output += 'Armour:\n'
        output += '\tHead: {}\n'.format(self.armour_set['head'])
        output += '\tChest: {}\n'.format(self.armour_set['chest'])
        output += '\tArms: {}\n'.format(self.armour_set['arms'])
        output += '\tWaist: {}\n'.format(self.armour_set['waist'])
        output += '\tLegs: {}\n'.format(self.armour_set['legs'])
        output += '\n'
        output += 'Defense:\n'
        output += '\tMinimum: {}\n'.format(min_defense)
        output += '\tMaximum: {}\n\n'.format(max_defense)
        output += 'Slots: {} ({})\n\n'.format('o' * slots, slots)
        output += 'Skills:\n\t'
        output += '\n\t'.join('{}: {}'.format(x, skill_points[x]) for x in
                              skill_points)
        output += '\n\n'
        output += 'Resistances:\n\t'
        output += '\n\t'.join('{}: {}'.format(x, res_points[x]) for x in
                              res_points)
        subprocess.Popen(['clipit', output])
        subprocess.Popen(['notify-send', 'Armour Set Searcher', 'The armour '
                          'set is now in your clipboard.'])
        return True


class SortType(Gtk.HBox):
    """SortType
    A widget for the type of sorting for the program.
    """

    def __init__(self):
        Gtk.HBox.__init__(self)
        title = Gtk.Label('Sort Type:')
        title.set_halign(Gtk.Align.START)
        self.set_homogeneous(True)
        self.pack_start(title, True, True, 10)
        self.list = Gtk.ListStore(str)
        self.list.append(['Default'])
        self.list.append(['Slots'])
        self.list.append(['Defense'])
        text_render = Gtk.CellRendererText()
        self.combo = Gtk.ComboBox.new_with_model(self.list)
        self.combo.pack_start(text_render, True)
        self.combo.add_attribute(text_render, "text", 0)
        self.combo.set_active(0)
        self.pack_start(self.combo, True, True, 10)


class Gender(Gtk.HBox):

    def __init__(self):
        Gtk.HBox.__init__(self)
        title = Gtk.Label('Gender:')
        title.set_halign(Gtk.Align.START)
        self.set_homogeneous(True)
        self.pack_start(title, True, True, 10)
        self.list = Gtk.ListStore(str)
        self.list.append(['Both'])
        self.list.append(['Male'])
        self.list.append(['Female'])
        text_render = Gtk.CellRendererText()
        self.combo = Gtk.ComboBox.new_with_model(self.list)
        self.combo.pack_start(text_render, True)
        self.combo.add_attribute(text_render, "text", 0)
        self.combo.set_active(0)
        self.pack_start(self.combo, True, True, 10)


class Weapon(Gtk.HBox):

    def __init__(self):
        Gtk.HBox.__init__(self)
        title = Gtk.Label('Weapon:')
        title.set_halign(Gtk.Align.START)
        self.set_homogeneous(True)
        self.pack_start(title, True, True, 10)
        self.list = Gtk.ListStore(str)
        self.list.append(['Both'])
        self.list.append(['Blademaster'])
        self.list.append(['Gunner'])
        text_render = Gtk.CellRendererText()
        self.combo = Gtk.ComboBox.new_with_model(self.list)
        self.combo.pack_start(text_render, True)
        self.combo.add_attribute(text_render, "text", 0)
        self.combo.set_active(0)
        self.pack_start(self.combo, True, True, 10)


class MinRarity(Gtk.HBox):

    def __init__(self):
        Gtk.HBox.__init__(self)
        title = Gtk.Label('Minimum Rarity:')
        title.set_halign(Gtk.Align.START)
        self.set_homogeneous(True)
        self.pack_start(title, True, True, 10)
        self.list = Gtk.ListStore(str)
        for i in range(1, 11):
            self.list.append([str(i)])
        text_render = Gtk.CellRendererText()
        self.combo = Gtk.ComboBox.new_with_model(self.list)
        self.combo.pack_start(text_render, True)
        self.combo.add_attribute(text_render, "text", 0)
        self.combo.set_active(0)
        self.pack_start(self.combo, True, True, 10)


class MaxRarity(Gtk.HBox):

    def __init__(self):
        Gtk.HBox.__init__(self)
        title = Gtk.Label('Maximum Rarity:')
        title.set_halign(Gtk.Align.START)
        self.set_homogeneous(True)
        self.pack_start(title, True, True, 10)
        self.list = Gtk.ListStore(str)
        for i in range(1, 11):
            self.list.append([str(i)])
        text_render = Gtk.CellRendererText()
        self.combo = Gtk.ComboBox.new_with_model(self.list)
        self.combo.pack_start(text_render, True)
        self.combo.add_attribute(text_render, "text", 0)
        self.combo.set_active(9)
        self.pack_start(self.combo, True, True, 10)


class MainWindow(Gtk.Window):
    """MainWindow
    The main GUI window for the searcher.
    """
    def __init__(self):
        Gtk.Window.__init__(self)

        self.connect('delete-event', Gtk.main_quit)
        self.create_widgets()
        self.show_all()

    def create_widgets(self):
        """create_widgets
        Creates all the widgets for the program.
        """
        self.grid = Gtk.Grid()
        self.grid.set_row_spacing(10)
        self.grid.set_column_spacing(10)
        self.skill_list = SkillList()
        self.search_button = SearchButton()
        self.result_area = ResultArea()
        self.separator = Gtk.Separator()
        self.sort_type = SortType()
        self.gender = Gender()
        self.weapon = Weapon()
        self.min_rarity = MinRarity()
        self.max_rarity = MaxRarity()

        self.grid.attach(self.skill_list, 0, 0, 5, 20)
        self.grid.attach(self.search_button, 0, 20, 5, 1)
        self.grid.attach(self.separator, 5, 17, 17, 1)
        self.grid.attach(self.result_area, 5, 0, 17, 17)
        self.grid.attach(self.sort_type, 5, 18, 8, 1)
        self.grid.attach(self.gender, 5, 20, 8, 1)
        self.grid.attach(self.weapon, 5, 19, 8, 1)
        self.grid.attach(self.min_rarity, 13, 18, 9, 1)
        self.grid.attach(self.max_rarity, 13, 19, 9, 1)
        self.add(self.grid)
        return None

    @AsThread()
    def search(self):
        """search
        Initiates the search for the program.
        """
        self.result_area.clear()
        self.search_button.disable()

        wanted_skills = [x[0] for x in self.skill_list.list if x[1] == True]
        sort_type = self.sort_type.list[self.sort_type.combo.get_active()][0]
        gender = self.gender.list[self.gender.combo.get_active()][0]
        weapon = self.weapon.list[self.weapon.combo.get_active()][0]
        min_rarity = self.min_rarity.list[
            self.min_rarity.combo.get_active()][0]
        max_rarity = self.max_rarity.list[
            self.max_rarity.combo.get_active()][0]

        self.result_area.add_search_string('Searching for {}.'.format(
                                           ', '.join(wanted_skills)))

        try:
            results = search(wanted_skills, gender, weapon)
            sorter = ArmourSort(wanted_skills, sort_type=sort_type)
            sorted_results = sorted(results, key=sorter.sort, reverse=True)
        except Exception:
            pass
        else:
            for index, item in enumerate(sorted_results[:100]):
                result = Result(index+1, item)
                self.result_area.add_result(result)

        self.search_button.enable()
        self.result_area.add_end_of_results()
        return None


class ArmourSort:
    """ArmourSort
    Sorts the armour combo's based on the skills you want and sort_type
    """

    def __init__(self, wanted_skills, sort_type='Default'):
        """__init__
        Creates the sort class, passing in the wanted_skills and sort_type
        now.

        params:
        wanted_skills:  list:   A list of the skills that you want in the set.
        sort_type:      str:    The type of sorting it will go off, Defense,
                                Skills, Resistance.
        """
        self.sort_type = sort_type
        self.skills = {}
        for name in wanted_skills:
            self.skills[name] = skills[name]['Points']

    def sort(self, armour_set):
        """sort
        Called by sorted()
        It has access to the variables we created before

        params:
        armour_set:     dict:       A mapping of the current armour set.

        returns:        int:        A score for the armour set.
                                    The higher the score the better the set
                                    is. This score is calculated based on
                                    what the user wants to be in the armour
                                    sets.
        """
        # Get the data about each piece
        head = armour[armour_set['head']]
        arms = armour[armour_set['arms']]
        chest = armour[armour_set['chest']]
        waist = armour[armour_set['waist']]
        legs = armour[armour_set['legs']]
        sort_points = 0

        # Increase the score based on the amount of slots the set has.
        # If you chose 'Slots' as the sort type the score for the slots
        # will be larger.
        sort_points += ((head['slots'] + arms['slots'] + chest['slots'] +
                        waist['slots'] + legs['slots']) *
                        (2 if self.sort_type == 'Slots' else 0.5))

        # Iterate through the skills you want to find in the set.
        for skill in self.skills:
            # Get the amount of points the skill needs to be active.
            skill_points = self.skills[skill]

            # Get the name of the gem / jewel you need for it.
            name = skills[skill]['Jewel']
            total_points = 0

            # Work out how close the skill in the set is to the skill that you
            # want. This score will be how far away the set's skill number is
            # from how many points the skill needs to be active. Higher or
            # lowe than required will get worse scores based on how far away
            # from the required number they are.
            if name in head['skills']:
                total_points += head['skills'][name]
            if name in chest['skills']:
                total_points += chest['skills'][name]
            if name in arms['skills']:
                total_points += arms['skills'][name]
            if name in waist['skills']:
                total_points += waist['skills'][name]
            if name in legs['skills']:
                total_points += legs['skills'][name]

            # If the total points the armour set has isn't quite as much as
            # you need it to be, deduct a little more than usual from the
            # score. If it is as much as you want, give it a better score.
            if total_points != skill_points:
               sort_points -= ((skill_points-total_points if skill_points >
                                total_points else
                                total_points-skill_points))*2
            else:
                sort_points -= ((skill_points-total_points if skill_points >
                                total_points else total_points-skill_points))

        # Add some points for how good the defense max is. If you choose
        # 'Defense' as the sort type this will put much more into the score
        # making the ones with high defense show at the top.
        sort_points += ((head['defense']['max'] +
                        chest['defense']['max'] +
                        arms['defense']['max'] +
                        waist['defense']['max'] +
                        legs['defense']['max']) * (500 if self.sort_type ==
                        'Defense' else 1))
        return sort_points


def search(wanted_skills, gender, weapon, size_limit=1000000,
           min_rarity=1, max_rarity=10, exclude=[]):
    """search
    Searches the list of pieces and generates possible combinations based
    on the params you enter.

    params:
    wanted_skills:      list:       A list of skills that you want in the set.
    gender:             str:        The gender (Male, Female, Both) of the
                                    pieces you want.
    weapon:             str:        The type of weapon (Gunner, Blademaster,
                                    Both) that the armour pieces get used
                                    with.
    size_limit:         int:        How many pieces to search through.
                                    Defaults to 1 million.
    min_rarity:         int:        The minimum rarity level of the items.
    max_rarity:         int:        The maximum rarity level of the items.
    exclude:            list:       A list of pieces that you don't want to
                                    see used in the set[s].
    """
    sets = []
    required_skills = {}

    # Get the names for the skills you entered.
    for skill_name in wanted_skills:
        if skill_name in skills:
            required_skills[skill_name] = skills[skill_name]

    # Create a list of all the possible items, it will also filter out any
    # armour pieces that aren't complying with gender and weapon.
    h_list = []
    a_list = []
    c_list = []
    w_list = []
    l_list = []

    # Create the list of head items
    for name in head_parts:
        if 'dummy' in name or name in exclude:
            continue
        item = head_parts[name]
        if item['rarity'] < min_rarity or item['rarity'] > max_rarity:
            continue
        if (not any(required_skills[x]['Jewel'] in item['skills'] for x in
                required_skills)):
            continue
        if (weapon == 'Both' or item['type'] == weapon and gender == 'Both' or
                item['gender'] == gender or item['gender'] == 'Both' or
                item['type'] == 'Both'):
            h_list.append(name)

    # Create the list of arm items
    for name in arm_parts:
        if 'dummy' in name or name in exclude:
            continue
        if item['rarity'] < min_rarity or item['rarity'] > max_rarity:
            continue
        item = arm_parts[name]
        if (not any(required_skills[x]['Jewel'] in item['skills'] for x in
                required_skills)):
            continue
        if (weapon == 'Both' or item['type'] == weapon and gender == 'Both' or
                item['gender'] == gender or item['gender'] == 'Both' or
                item['type'] == 'Both'):
            a_list.append(name)

    # Create the list of chest items
    for name in chest_parts:
        if 'dummy' in name or name in exclude:
            continue
        if item['rarity'] < min_rarity or item['rarity'] > max_rarity:
            continue
        item = chest_parts[name]
        if (not any(required_skills[x]['Jewel'] in item['skills'] for x in
                required_skills)):
            continue
        if (weapon == 'Both' or item['type'] == weapon and gender == 'Both' or
                item['gender'] == gender or item['gender'] == 'Both' or
                item['type'] == 'Both'):
            c_list.append(name)

    # Create the list of waist items
    for name in waist_parts:
        if 'dummy' in name or name in exclude:
            continue
        if item['rarity'] < min_rarity or item['rarity'] > max_rarity:
            continue
        item = waist_parts[name]
        if (not any(required_skills[x]['Jewel'] in item['skills'] for x in
                required_skills)):
            continue
        if (weapon == 'Both' or item['type'] == weapon and gender == 'Both' or
                item['gender'] == gender or item['gender'] == 'Both' or
                item['type'] == 'Both'):
            w_list.append(name)

    # Create the list of leg items
    for name in leg_parts:
        if 'dummy' in name or name in exclude:
            continue
        if item['rarity'] < min_rarity or item['rarity'] > max_rarity:
            continue
        item = leg_parts[name]
        if (not any(required_skills[x]['Jewel'] in item['skills'] for x in
                required_skills)):
            continue
        if (weapon == 'Both' or item['type'] == weapon and gender == 'Both' or
                item['gender'] == gender or item['gender'] == 'Both' or
                item['type'] == 'Both'):
            l_list.append(name)

    h_index = 0
    a_index = 0
    c_index = 0
    l_index = 0
    w_index = 0
    items = 0

    h_list = sorted(h_list)
    a_list = sorted(a_list)
    c_list = sorted(c_list)
    w_list = sorted(w_list)
    l_list = sorted(l_list)

    # Here is where the magic happens.
    # This part generates every possible combination from the left over lists
    # of parts. It also stops and waits for 5 seconds each million'th item to
    # prevent massive CPU hogging.
    while True:
        h_choice = h_list[h_index]
        c_choice = c_list[c_index]
        a_choice = a_list[a_index]
        w_choice = w_list[w_index]
        l_choice = l_list[l_index]
        current_set = {'head': h_choice, 'chest': c_choice, 'arms': a_choice,
                       'waist': w_choice, 'legs': l_choice}
        yield current_set
        items += 1
        h_index += 1
        if h_index == len(h_list):
            h_index = 0
            a_index += 1
        if a_index == len(a_list):
            a_index = 0
            c_index += 1
        if c_index == len(c_list):
            c_index = 0
            w_index += 1
        if w_index == len(w_list):
            w_index = 0
            l_index += 1
        if (l_index == len(l_list) or size_limit is not None and items ==
                size_limit):
            break
        if items+1 % 1000000 == 0:
            time.sleep(10)
    return None


def main():
    window = MainWindow()
    try:
        Gtk.main()
    except KeyboardInterrupt:
        Gtk.main_quit()
    return None


# Opens all the files and load in the data once.
with open('data/armour.json', 'r') as fp:
    armour = json.loads(fp.read())
with open('data/jewels.json', 'r') as fp:
    jewels = json.loads(fp.read())
with open('data/skills.json', 'r') as fp:
    skills = json.loads(fp.read())


# Parse through all the armour pieces and sort them to their part.
head_parts = {x: armour[x] for x in armour if armour[x]['part'] == 'Head'}
arm_parts = {x: armour[x] for x in armour if armour[x]['part'] == 'Arms'}
chest_parts = {x: armour[x] for x in armour if armour[x]['part'] == 'Chest'}
leg_parts = {x: armour[x] for x in armour if armour[x]['part'] == 'Legs'}
waist_parts = {x: armour[x] for x in armour if armour[x]['part'] == 'Waist'}


print('Loaded {} armour pieces in total.'.format(len(armour)))
print('Loaded {} head pieces.'.format(len(head_parts)))
print('Loaded {} arm pieces.'.format(len(arm_parts)))
print('Loaded {} chest pieces.'.format(len(chest_parts)))
print('Loaded {} leg pieces.'.format(len(leg_parts)))
print('Loaded {} waist pieces.'.format(len(waist_parts)))


if __name__ == '__main__':
    main()
