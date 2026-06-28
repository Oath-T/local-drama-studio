import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";

import { Button } from "./button";
import { Dialog, DialogContent, DialogTitle, DialogTrigger } from "./dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./select";

function DialogSelectFixture() {
  const [value, setValue] = useState("alpha");

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button type="button">打开</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogTitle>选择测试</DialogTitle>
        <Select value={value} onValueChange={setValue}>
          <SelectTrigger aria-label="测试选项">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="alpha">Alpha</SelectItem>
            <SelectItem value="beta">Beta</SelectItem>
          </SelectContent>
        </Select>
        <div>当前：{value}</div>
      </DialogContent>
    </Dialog>
  );
}

describe("Select", () => {
  it("opens and selects an item inside a dialog portal", async () => {
    const user = userEvent.setup();
    render(<DialogSelectFixture />);

    await user.click(screen.getByRole("button", { name: "打开" }));
    await user.click(screen.getByRole("combobox", { name: "测试选项" }));
    await user.click(await screen.findByRole("option", { name: "Beta" }));

    expect(screen.getByText("当前：beta")).toBeInTheDocument();
  });
});
