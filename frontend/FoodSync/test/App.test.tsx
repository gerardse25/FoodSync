import { render } from "@testing-library/react-native";
import React from "react";
import Index from "../src/app/index";

describe("<Index />", () => {
  it("se renderiza correctamente", () => {
    const { getByText } = render(<Index />);
    expect(getByText("Gestión inteligente de neveras y compras")).toBeTruthy();
  });
});
