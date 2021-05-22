from tkinter import Frame, StringVar, TOP, LEFT, Label, RIGHT, BOTTOM, END, Tk, Entry, Listbox

# First create application class
from typing import List


class SearchListbox(Frame):

    def __init__(self, master: Frame, items: List[str]):
        Frame.__init__(self, master)
        self.items = items
        self.pack()
        self.create_widgets()

        # Create main GUI window

    def create_widgets(self):
        self.search_var = StringVar()
        self.search_var.trace_add("write", self.update_list)
        top_frame = Frame(self)
        top_frame.pack(side=TOP, expand=True, fill='both')
        self.entry = Entry(top_frame, textvariable=self.search_var, width=24)
        self.entry.pack(side=LEFT, fill="x")
        self.current_label = Label(top_frame, text="Hello")
        self.current_label.pack(side=RIGHT, padx=10)

        self.lbox = Listbox(self, width=45, height=25)
        self.fill_listbox(self.items)

        self.lbox.pack(side=BOTTOM, expand=True, fill='both')

        def callback(event):
            selection = event.widget.curselection()
            if selection:
                index = selection[0]
                data = event.widget.get(index)
                self.current_label.configure(text=data)
            else:
                self.current_label.configure(text="")

        self.lbox.bind("<<ListboxSelect>>", callback)

    def update_list(self, *args):
        search_term = self.search_var.get()
        items = [x for x in self.items if search_term.lower() in x.lower()]
        self.fill_listbox(items)

    def fill_listbox(self, items: List[str]):
        self.lbox.delete(0, END)
        for item in items:
            self.lbox.insert(END, item)

    def get_selection(self) -> str:
        return self.current_label['text']


def search_listbox_test():
    root = Tk()
    root.title('Filter Listbox Test')
    lst = ['Adam', 'Lucy', 'Barry', 'Bob', 'James', 'Frank', 'Susan', 'Amanda', 'Christie']
    app = SearchListbox(master=root, items=lst * 3)
    app.mainloop()


if __name__ == '__main__':
    search_listbox_test()
    # pianoroll_test()
