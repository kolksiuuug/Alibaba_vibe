import { ScrollArea, Table } from "@mantine/core";

import type { Schemas } from "../api/client";
import { formatMoneyExact } from "../shared/format";

export function ScheduleTable({ rows }: { rows: Schemas["ScheduleRow"][] }) {
  return (
    <ScrollArea.Autosize mah={360}>
      <Table striped stickyHeader verticalSpacing={4}>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Месяц</Table.Th>
            <Table.Th ta="right">Платёж</Table.Th>
            <Table.Th ta="right">Основной долг</Table.Th>
            <Table.Th ta="right">Проценты</Table.Th>
            <Table.Th ta="right">Остаток долга</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {rows.map((row) => (
            <Table.Tr key={row.number}>
              <Table.Td>{row.number}</Table.Td>
              <Table.Td ta="right">{formatMoneyExact(row.payment)}</Table.Td>
              <Table.Td ta="right">{formatMoneyExact(row.principal)}</Table.Td>
              <Table.Td ta="right">{formatMoneyExact(row.interest)}</Table.Td>
              <Table.Td ta="right">{formatMoneyExact(row.balance)}</Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </ScrollArea.Autosize>
  );
}
