#!/usr/bin/env python3
"""MH4U Armour Set Searcher
A simple armour set creator and searcher for Monster Hunter 4U.
"""


import json
import time
import os
import subprocess
import threading
from gi.repository import Gtk, Gdk, GLib


class AsThread:
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
        check_render.set_padding(10, 15)
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
        print('Populating skill list.')
        self.list.clear()
        for skill_name in sorted(skills):
            self.list.append([skill_name, 0, '{} ({} {:+})'.format(skills[
                              skill_name]['Description'],
                              skills[skill_name]['Jewel'],
                              int(skills[skill_name]['Points']))])
        return None

    def clicked(self, view, path, _):
        """clicked
        Called when the user clicks a row, it will toggle the checkbox.
        """
        index = int(path.to_string())
        print('Skill "{}" clicked.'.format(self.list[index][0]))
        self.list[index][1] = not self.list[index][1]
        return None

    def check_column_clicked(self, *_):
        """check_column_clicked
        Gets called when you click the title of the check colums,
        This will set all skills to unchecked.
        """
        print('Clearing skill list.')
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
        # If there is a better way to do this id be happy to see it.
        print('Searching.')
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
        print('Clearing result area.')
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
        self.index = index
        self.armour_set = armour_set
        h_piece = armour_set['head']['name']
        c_piece = armour_set['chest']['name']
        a_piece = armour_set['arms']['name']
        w_piece = armour_set['waist']['name']
        l_piece = armour_set['legs']['name']
        def_min = 0
        def_max = 0
        total_slots = 0
        for piece in armour_set:
            if (isinstance(piece, int) or piece
                    not in ['head', 'chest', 'arms', 'waist', 'legs']):
                continue
            name = armour_set[piece]['name']
            def_min += armour[name]['defense']['min']
            def_max += armour[name]['defense']['max']
            total_slots += armour[name]['slots']

        skill_points = {}
        for piece in armour_set:
            if isinstance(piece, int):
                continue
            if piece not in ['head', 'arms', 'chest', 'legs', 'waist']:
                continue
            name = armour_set[piece]['name']
            for skill in armour[name]['skills']:
                if skill not in skill_points:
                    skill_points[skill] = armour[name]['skills'][skill]
                else:
                    skill_points[skill] += armour[name]['skills'][skill]
        jewel_names = []
        for index, slot in enumerate(armour_set['slots']):
            jewel_names.append([])
            for jewel in slot:
                if jewel == {}:
                    continue
                jname = list(jewel.keys())[0]
                for skill in jewel[jname]['Skills']:
                    if skill not in skill_points:
                        skill_points[skill] = 0
                    skill_points[skill] += jewel[jname]['Skills'][skill]
                total_slots -= int(jewel[jname]['Slots'])
                jewel_names[index].append(jname)

        set_box = Gtk.VBox()
        title = Gtk.Label()
        title.set_halign(Gtk.Align.START)
        pnts = armour_set['points']
        if pnts == 0:
            color = '#0F0'
        elif pnts > -5:
            color = '#3A0'
        elif pnts > -10:
            color = '#AA0'
        else:
            color = '#F00'
        points = '<span foreground="{}">Points: {}</span>'.format(color, pnts)
        title.set_markup('<span size="xx-large" foreground="#999"><a '
                         'href="#">Result {}</a></span> ({})'.format(
                        self.index, points))
        title.connect('activate-link', self.clicked)
        set_box.pack_start(title, True, True, 20)
        set_title = Gtk.Label()
        set_title.set_markup('<span font-weight="bold">Armour Pieces:</span>')
        set_title.set_halign(Gtk.Align.START)
        head_name = Gtk.Label()
        head_name.set_markup('\t<span font-weight="bold">Head:</span>\t{'
                             '}\n\t\t\t\t{}'.format(h_piece,
                             '\n\t\t\t\t'.join(jewel_names[0])))
        head_name.set_halign(Gtk.Align.START)
        head_name.set_tooltip_text(json.dumps(armour[h_piece], indent='\t'))
        chest_name = Gtk.Label()
        chest_name.set_markup('\t<span font-weight="bold">Chest:</span>\t{'
                              '}\n\t\t\t\t{}'.format(c_piece,
                              '\n\t\t\t\t'.join(jewel_names[1])))
        chest_name.set_halign(Gtk.Align.START)
        chest_name.set_tooltip_text(json.dumps(armour[c_piece], indent='\t'))
        arms_name = Gtk.Label()
        arms_name.set_markup('\t<span font-weight="bold">Arms:</span>\t{'
                             '}\n\t\t\t\t{}'.format(a_piece,
                             '\n\t\t\t\t'.join(jewel_names[2])))
        arms_name.set_halign(Gtk.Align.START)
        arms_name.set_tooltip_text(json.dumps(armour[a_piece], indent='\t'))
        waist_name = Gtk.Label()
        waist_name.set_markup('\t<span font-weight="bold">Waist:</span>\t{'
                              '}\n\t\t\t\t{}'.format(w_piece,
                              '\n\t\t\t\t'.join(jewel_names[3])))
        waist_name.set_halign(Gtk.Align.START)
        waist_name.set_tooltip_text(json.dumps(armour[w_piece], indent='\t'))
        legs_name = Gtk.Label()
        legs_name.set_markup('\t<span font-weight="bold">Legs:</span>\t{'
                             '}\n\t\t\t\t{}'.format(l_piece,
                             '\n\t\t\t\t'.join(jewel_names[4])))
        legs_name.set_halign(Gtk.Align.START)
        legs_name.set_tooltip_text(json.dumps(armour[l_piece], indent='\t'))
        defense_title = Gtk.Label()
        defense_title.set_markup('<span font-weight="bold">Defense:</span>')
        defense_title.set_halign(Gtk.Align.START)


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
            amount = int(skill_points[skill])
            skill_list.append([skill, amount])
        self.pack_start(scroll, True, True, 10)

    def clicked(self, *params):
        """clicked
        Generates a simple output of the selected output and copies
        it to your clipboard.
        """
        print('Result {} clicked'.format(self.index))
        max_defense = 0
        min_defense = 0
        skill_points = {}
        res_points = {}
        slots = 0
        output = ''
        for piece in self.armour_set:
            if piece in ['head', 'arms', 'legs', 'waist', 'chest']:
                name = self.armour_set[piece]['name']
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
        jewel_names = []
        for index, slot in enumerate(self.armour_set['slots']):
            jewel_names.append([])
            for jewel in slot:
                if jewel == {}:
                    continue
                jname = list(jewel.keys())[0]
                for skill in jewel[jname]['Skills']:
                    if skill not in skill_points:
                        skill_points[skill] = 0
                    skill_points[skill] += jewel[jname]['Skills'][skill]
                slots -= int(jewel[jname]['Slots'])
                jewel_names[index].append(jname)
        output += 'Armour:\n'
        output += '\tHead: {}\n\t\t\t\t{}\n'.format(self.armour_set['head']['name'],
                  '\n\t\t\t\t'.join(jewel_names[0]))
        output += '\tChest: {}\n\t\t\t\t{}\n'.format(self.armour_set['chest']['name'],
                  '\n\t\t\t\t'.join(jewel_names[1]))
        output += '\tWaist: {}\n\t\t\t\t{}\n'.format(self.armour_set['waist']['name'],
                  '\n\t\t\t\t'.join(jewel_names[2]))
        output += '\tArms: {}\n\t\t\t\t{}\n'.format(self.armour_set['arms']['name'],
                  '\n\t\t\t\t'.join(jewel_names[3]))
        output += '\tLegs: {}\n\t\t\t\t{}\n'.format(self.armour_set['legs']['name'],
                  '\n\t\t\t\t'.join(jewel_names[4]))
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
        #self.list.append(['Accurate Skill'])
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


class JewelsCount(Gtk.CheckButton):
    def __init__(self):
        Gtk.CheckButton.__init__(self, 'Jewels count as another set')


class Game(Gtk.ComboBox):
    def __init__(self):
        Gtk.ComboBox.__init__(self)
        self.list = Gtk.ListStore(str)
        games = os.listdir('data/')
        for i in games:
            self.list.append([i])
        text_render = Gtk.CellRendererText()
        self.set_model(self.list)
        self.pack_start(text_render, True)
        self.add_attribute(text_render, 'text', 0)
        for i, v in enumerate(games):
            if v == game:
                self.set_active(i)
        self.connect('changed', self.clicked)

    def clicked(self, widget):
        global game, armour, head_parts, arm_parts, chest_parts, waist_parts, leg_parts, jewels, skills
        index = self.get_active()
        game = self.list[index][0]

        with open('use_game.txt', 'w') as f:
            f.write(game)

        # Opens all the files and load in the data once.
        with open('data/{}/armour.json'.format(game), 'r') as fp:
            armour = json.loads(fp.read())
        with open('data/{}/jewels.json'.format(game), 'r') as fp:
            jewels = json.loads(fp.read())
        with open('data/{}/skills.json'.format(game), 'r') as fp:
            skills = json.loads(fp.read())


        # Parse through all the armour pieces and sort them to their part.
        head_parts = sorted({x: armour[x] for x in armour if armour[x]['part'] == 'Head'}, key=piece_sort)
        arm_parts = sorted({x: armour[x] for x in armour if armour[x]['part'] == 'Arms'}, key=piece_sort)
        chest_parts = sorted({x: armour[x] for x in armour if armour[x]['part'] == 'Chest'}, key=piece_sort)
        leg_parts = sorted({x: armour[x] for x in armour if armour[x]['part'] == 'Legs'}, key=piece_sort)
        waist_parts = sorted({x: armour[x] for x in armour if armour[x]['part'] == 'Waist'}, key=piece_sort)


        print('Loaded {} armour pieces in total.'.format(len(armour)))
        print('Loaded {} head pieces.'.format(len(head_parts)))
        print('Loaded {} arm pieces.'.format(len(arm_parts)))
        print('Loaded {} chest pieces.'.format(len(chest_parts)))
        print('Loaded {} leg pieces.'.format(len(leg_parts)))
        print('Loaded {} waist pieces.'.format(len(waist_parts)))

        main_window = self.get_toplevel()
        main_window.skill_list.populate()
        return None


class MainWindow(Gtk.Window):
    """MainWindow
    The main GUI window for the searcher.
    """
    def __init__(self):
        Gtk.Window.__init__(self)

        self.connect('delete-event', Gtk.main_quit)
        self.create_widgets()
        self.show_all()
        print('Showing window.')

    def create_widgets(self):
        """create_widgets
        Creates all the widgets for the program.
        """
        print('Creating widgets.')
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
        self.jewels_count = JewelsCount()
        self.game = Game()
        self.grid.attach(self.game, 0, 0, 7, 1)
        self.grid.attach(self.skill_list, 0, 1, 7, 19)
        self.grid.attach(self.search_button, 0, 20, 7, 1)
        self.grid.attach(self.separator, 7, 17, 17, 1)
        self.grid.attach(self.result_area, 7, 0, 17, 17)
        self.grid.attach(self.sort_type, 7, 18, 8, 1)
        self.grid.attach(self.gender, 7, 20, 8, 1)
        self.grid.attach(self.weapon, 7, 19, 8, 1)
        self.grid.attach(self.min_rarity, 15, 18, 9, 1)
        self.grid.attach(self.max_rarity, 15, 19, 9, 1)
        #self.grid.attach(self.jewels_count, 15, 20, 9, 1)
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
        jewels_count = self.jewels_count.get_active()
        min_rarity = int(self.min_rarity.list[
            self.min_rarity.combo.get_active()][0])
        max_rarity = int(self.max_rarity.list[
            self.max_rarity.combo.get_active()][0])
        self.result_area.add_search_string('Searching for {}.'.format(
                                           ', '.join(wanted_skills)))

        try:
            results = generate_combos(wanted_skills, armour, skills, jewels,
                             gender, weapon, gems_count=jewels_count)
            sorter = ArmourSort(wanted_skills, sort_type=sort_type)
            print('Sorting, please wait.')
            sorted_results = sorted(results, key=sorter.sort, reverse=True)
        except Exception:
            raise
        else:
            print('Showing results.')
            for index, item in enumerate(sorted_results[:100]):
                result = Result(index+1, item)
                self.result_area.add_result(result)

        print('Done.')
        self.search_button.enable()
        self.result_area.add_end_of_results()
        return None


class ArmourSort:
    def __init__(self, wanted_skills, sort_type='Default'):
        self.wanted_skills = {}
        for name in wanted_skills:
            self.wanted_skills[name] = skills[name]['Points']
        print( self.wanted_skills )
        self.sort_type = sort_type

    def sort(self, aset):
        head = aset['head']
        chest = aset['chest']
        arms = aset['arms']
        waist = aset['waist']
        legs = aset['legs']
        hjl = []
        cjl = []
        ajl = []
        wjl = []
        ljl = []
        for item in aset['slots'][0]:
            if item == {}:
                continue
            hjl.append(item[list(item.keys())[0]])
        for item in aset['slots'][1]:
            if item == {}:
                continue
            cjl.append(item[list(item.keys())[0]])
        for item in aset['slots'][2]:
            if item == {}:
                continue
            ajl.append(item[list(item.keys())[0]])
        for item in aset['slots'][3]:
            if item == {}:
                continue
            wjl.append(item[list(item.keys())[0]])
        for item in aset['slots'][4]:
            if item == {}:
                continue
            ljl.append(item[list(item.keys())[0]])

        total_points = 0
        for skill in self.wanted_skills:
            skill_points = self.wanted_skills[skill]
            name = skills[skill]['Jewel']
            torso_up = ('Torso Up' in head['skills'] or
                       'Torso Up' in chest['skills'] or
                       'Torso Up' in arms['skills'] or
                       'Torso Up' in waist['skills'] or
                       'Torso Up' in legs['skills'])
            if torso_up:
                for skill in chest['skills']:
                    chest['skill'][name] = chest['skill'][name] * 2
                points += 100
            points = 0
            if name in head['skills']:
                sp = int(head['skills'][name])
                points += sp
            if name in chest['skills']:
                sp = int(chest['skills'][name])
                if torso_up:
                    sp = sp * 2
                points += sp
            if name in arms['skills']:
                sp = int(arms['skills'][name])
                points += sp
            if name in waist['skills']:
                sp = int(waist['skills'][name])
                points += sp
            if name in legs['skills']:
                sp = int(legs['skills'][name])
                points += sp
            for hj in hjl:
                if hj is not None and name in hj['Skills']:
                    sp =  int(hj['Skills'][name])
                    points += sp
            for cj in cjl:
                if cj is not None and name in cj['Skills']:
                    sp =  int(cj['Skills'][name])
                    points += sp
            for aj in ajl:
                if aj is not None and name in aj['Skills']:
                    sp =  int(aj['Skills'][name])
                    points += sp
            for wj in wjl:
                if wj is not None and name in wj['Skills']:
                    sp =  int(wj['Skills'][name])
                    points += sp
            for lj in ljl:
                if lj is not None and name in lj['Skills']:
                    sp =  int(lj['Skills'][name])
                    points += sp
            total_points -= ((int(skill_points)-points if int(skill_points)
                              > points else points-int(skill_points)))
        aset['points'] = total_points
        if self.sort_type == 'Defense':
            defense = (head['defense']['max'] + arms['defense']['max']
                       + chest['defense']['max'] + waist['defense']['max']
                       + legs['defense']['max'])
            total_points -= (10000-(defense/10000))
        if self.sort_type == 'Slots':
            slots = (head['slots'] + arms['slots'] + chest['slots']
                     + waist['slots'] + legs['slots'])
            total_points -= (100-(slots/100))
        return total_points


class PieceSort:
    def __init__(self, wanted_skills, sort_type='Default'):
        self.wanted_skills = {}
        for name in wanted_skills:
            self.wanted_skills[name] = skills[name]['Points']
        self.sort_type = sort_type

    def sort(self, aset):
        total = 0
        for skill in aset['skills']:
            if skill in self.wanted_skills:
                total += aset['skills'][skill]
        return total


def jewel_name(item):
    return list(item.keys())[0]


def generate_combos(wanted_skills, armour, skills, jewels, gender, weapon,
                    only_skilled=True, gems_count=False, size_limit=400000):
    sets = []
    head = []
    arms = []
    chest = []
    waist = []
    legs = []
    jls = [{'No Jewel': {'Points': 0, 'Slots': 0}}]
    required_skills = {}

    for skill_name in wanted_skills:
        if skill_name in skills:
            required_skills[skill_name] = skills[skill_name]

    for name in head_parts:
        item = armour[name]
        item['name'] = name
        if (only_skilled and (not any(required_skills[x]['Jewel'] in
                item['skills'] for x in required_skills) or 'Torso Up' in
                item['skills'])):
            continue
        if ((weapon == item['type'] or item['type'] == 'Both' or
                weapon == 'Both') and (gender == item['gender'] or
                gender == 'Both')):
            head.append(item)

    sorter = PieceSort(required_skills)
    head = sorted(head, key=sorter.sort)

    for name in chest_parts:
        item = armour[name]
        item['name'] = name
        if only_skilled and (not any(required_skills[x]['Jewel'] in
                item['skills']
                for x in required_skills) or 'Torso Up' in item['skills']):
            continue
        if ((weapon == item['type'] or item['type'] == 'Both' or
                weapon == 'Both') and (gender == item['gender'] or
                gender == 'Both')):
            chest.append(item)

    sorter = PieceSort(required_skills)
    chest = sorted(chest, key=sorter.sort)

    for name in arm_parts:
        item = armour[name]
        item['name'] = name
        if only_skilled and (not any(required_skills[x]['Jewel'] in
                item['skills']
                for x in required_skills) or 'Torso Up' in item['skills']):
            continue
        if ((weapon == item['type'] or item['type'] == 'Both' or
                weapon == 'Both') and (gender == item['gender'] or
                gender == 'Both')):
            arms.append(item)

    sorter = PieceSort(required_skills)
    arms = sorted(arms, key=sorter.sort)

    for name in waist_parts:
        item = armour[name]
        item['name'] = name
        if only_skilled and (not any(required_skills[x]['Jewel'] in
                item['skills']
                for x in required_skills) or 'Torso Up' in item['skills']):
            continue
        if ((weapon == item['type'] or item['type'] == 'Both' or
                weapon == 'Both') and (gender == item['gender'] or
                gender == 'Both')):
            waist.append(item)

    sorter = PieceSort(required_skills)
    waist = sorted(waist, key=sorter.sort)

    for name in leg_parts:
        item = armour[name]
        item['name'] = name
        if only_skilled and (not any(required_skills[x]['Jewel'] in
                item['skills']
                for x in required_skills) or 'Torso Up' in item['skills']):
            continue
        if ((weapon == item['type'] or item['type'] == 'Both' or
                weapon == 'Both') and (gender == item['gender'] or
                gender == 'Both')):
            legs.append(item)

    sorter = PieceSort(required_skills)
    legs = sorted(legs, key=sorter.sort)

    for item in sorted(jewels, reverse=True, key=jewel_name):
        name = list(item.keys())[0]
        if (not any(required_skills[x]['Jewel'] in item[name]['Skills']
                for x in required_skills)):
                    continue
        cn = 0
        for skill in required_skills:
            sname = required_skills[skill]['Jewel']
            if (sname in item[name]['Skills']
                    and int(required_skills[skill]['Points']) > 0
                    and int(item[name]['Skills'][sname]) < 0):
                cn += 1
        if cn != len(required_skills):
            jls.append(item)

    hi = ci = ai = wi = li = hji = cji = aji = wji = lji = 0
    index = 0
    while True:
        if (len(head) == 0 or len(chest) == 0 or len(arms) == 0 or
                len(waist) == 0 or len(legs) == 0):
            raise StopIteration
        hc = head[hi]
        cc = chest[ci]
        ac = arms[ai]
        wc = waist[wi]
        lc = legs[li]

        hjn = list(jls[hji].keys())[0]
        cjn = list(jls[cji].keys())[0]
        ajn = list(jls[aji].keys())[0]
        wjn = list(jls[wji].keys())[0]
        ljn = list(jls[lji].keys())[0]

        if hji == 0:
            hj = [{}]
        else:
            hj = [jls[hji]] * (int(hc['slots']) // int(jls[hji][hjn]['Slots']))
        if cji == 0:
            cj = [{}]
        else:
            cj = [jls[cji]] * (int(cc['slots']) // int(jls[cji][cjn]['Slots']))
        if aji == 0:
            aj = [{}]
        else:
            aj = [jls[aji]] * (int(ac['slots']) // int(jls[aji][ajn]['Slots']))
        if wji == 0:
            wj = [{}]
        else:
            wj = [jls[wji]] * (int(wc['slots']) // int(jls[wji][wjn]['Slots']))
        if lji == 0:
            lj = [{}]
        else:
            lj = [jls[lji]] * (int(lc['slots']) // int(jls[lji][ljn]['Slots']))
        yield {'head': hc, 'chest': cc, 'arms': ac, 'waist': wc, 'legs': lc,
               'slots': [hj, cj, aj, wj, lj]}
        hji += 1
        if hji == len(jls):
            hji = 0
            cji += 1
        if cji == len(jls):
            cji = 0
            aji += 1
        if aji == len(jls):
            aji = 0
            wji += 1
        if wji == len(jls):
            wji = 0
            lji += 1
        if lji == len(jls):
            lji = 0
            if gems_count:
                hi += 1
        if not gems_count:
            hi += 1
        if hi == len(head):
            hi = 0
            ci += 1
        if ci == len(chest):
            ci = 0
            ai += 1
        if ai == len(arms):
            ai = 0
            wi += 1
        if wi == len(waist):
            wi = 0
            li += 1
        if li == len(legs) or size_limit is not None and size_limit < index:
            break
        index += 1
        if (index+1) % 100000 == 0:
            time.sleep(0.5)
    raise StopIteration


def main():
    window = MainWindow()
    try:
        Gtk.main()
    except KeyboardInterrupt:
        Gtk.main_quit()
    return None


def piece_sort(piece):
    item = armour[piece]
    return (str(not bool('Torso Up' in item['skills'])) +
           str(-int(item['rarity'])) + piece)


with open('use_game.txt') as f:
    game = f.read().strip()


# Opens all the files and load in the data once.
with open('data/{}/armour.json'.format(game), 'r') as fp:
    armour = json.loads(fp.read())
with open('data/{}/jewels.json'.format(game), 'r') as fp:
    jewels = json.loads(fp.read())
with open('data/{}/skills.json'.format(game), 'r') as fp:
    skills = json.loads(fp.read())


# Parse through all the armour pieces and sort them to their part.
head_parts = sorted({x: armour[x] for x in armour if armour[x]['part']
                    == 'Head'}, key=piece_sort)
arm_parts = sorted({x: armour[x] for x in armour if armour[x]['part']
                    == 'Arms'}, key=piece_sort)
chest_parts = sorted({x: armour[x] for x in armour if armour[x]['part']
                    == 'Chest'}, key=piece_sort)
leg_parts = sorted({x: armour[x] for x in armour if armour[x]['part']
                    == 'Legs'}, key=piece_sort)
waist_parts = sorted({x: armour[x] for x in armour if armour[x]['part']
                    == 'Waist'}, key=piece_sort)


print('Loaded {} armour pieces in total.'.format(len(armour)))
print('Loaded {} head pieces.'.format(len(head_parts)))
print('Loaded {} arm pieces.'.format(len(arm_parts)))
print('Loaded {} chest pieces.'.format(len(chest_parts)))
print('Loaded {} leg pieces.'.format(len(leg_parts)))
print('Loaded {} waist pieces.'.format(len(waist_parts)))


if __name__ == '__main__':
    main()
