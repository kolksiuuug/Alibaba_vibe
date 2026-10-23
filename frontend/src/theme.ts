import { createTheme, type MantineColorsTuple } from "@mantine/core";

// Фирменный красный, близкий к цветам Альфа-Банка (использовать можно, не обязательно)
const alfa: MantineColorsTuple = [
  "#ffe9e7",
  "#ffd3cf",
  "#fca59e",
  "#f8746a",
  "#f54b3f",
  "#ef3124",
  "#e02417",
  "#c7170b",
  "#b10f07",
  "#9a0500",
];

export const theme = createTheme({
  primaryColor: "alfa",
  colors: { alfa },
  defaultRadius: "md",
  fontFamily: "system-ui, -apple-system, 'Segoe UI', Roboto, Arial, sans-serif",
  headings: { fontWeight: "700" },
});
