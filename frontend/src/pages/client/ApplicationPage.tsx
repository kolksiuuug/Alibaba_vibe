import { Alert, Anchor, Card, Grid, Group, Stack, Text, Title } from "@mantine/core";
import { IconInfoCircle } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import type { Schemas } from "../../api/client";
import { Api } from "../../api/endpoints";
import { StatusBadge } from "../../components/badges";
import { ErrorAlert, PageLoader } from "../../components/common";
import { EventsTimeline } from "../../components/EventsTimeline";
import { PipelineSteps } from "../../components/PipelineSteps";
import { purposeLabel } from "../../shared/dictionaries";
import { formatMoney, formatMonths } from "../../shared/format";
import { POLL_INTERVAL_MS, POLLING_STATUSES, statusInfo } from "../../shared/statuses";
import { DraftForm } from "./sections/DraftForm";
import { InfoRequestForm } from "./sections/InfoRequestForm";
import { OfferPanel } from "./sections/OfferPanel";
import {
  CheckingPanel,
  ClosedPanel,
  IssuedPanel,
  ManualReviewPanel,
  RejectedPanel,
  SignedPanel,
} from "./sections/Outcomes";
import { SignPanel } from "./sections/SignPanel";

function MainSection({ detail }: { detail: Schemas["ApplicationDetail"] }) {
  const status = detail.application.status;
  switch (status) {
    case "draft":
      return <DraftForm key={detail.application.id} detail={detail} />;
    case "submitted":
    case "checking":
      return <CheckingPanel detail={detail} />;
    case "info_requested":
      return <InfoRequestForm detail={detail} />;
    case "manual_review":
      return <ManualReviewPanel detail={detail} />;
    case "offer":
      return <OfferPanel detail={detail} />;
    case "accepted":
      return <SignPanel detail={detail} />;
    case "signed":
      return <SignedPanel />;
    case "issued":
      return <IssuedPanel detail={detail} />;
    case "rejected":
      return <RejectedPanel detail={detail} />;
    default:
      return <ClosedPanel text={statusInfo(status).client} />;
  }
}

export function ApplicationPage() {
  const id = Number(useParams().id);
  const query = useQuery({
    queryKey: ["application", id],
    queryFn: () => Api.application(id),
    refetchInterval: (q) =>
      POLLING_STATUSES.has(q.state.data?.application.status ?? "") ? POLL_INTERVAL_MS : false,
  });
  const status = query.data?.application.status;
  const events = useQuery({
    queryKey: ["events", id, status],
    queryFn: () => Api.events(id),
    enabled: Boolean(status),
  });

  if (query.isPending) return <PageLoader />;
  if (query.isError) return <ErrorAlert error={query.error} title="Заявка не открылась" />;

  const detail = query.data;
  const application = detail.application;
  const info = statusInfo(application.status);

  return (
    <Stack>
      <Group justify="space-between" align="flex-start">
        <div>
          <Text size="sm" c="dimmed">
            <Anchor component={Link} to="/">
              Мои заявки
            </Anchor>{" "}
            / Заявка №{application.id}
          </Text>
          <Title order={2}>{application.product.name}</Title>
          <Text c="dimmed">
            {formatMoney(application.amount)} на {formatMonths(application.term_months)} ·{" "}
            {purposeLabel(application.purpose)}
          </Text>
        </div>
        <StatusBadge status={application.status} size="lg" testId="application-status" />
      </Group>

      <Alert color={info.color} title="Что сейчас происходит" icon={<IconInfoCircle size={18} />}>
        {info.client}
      </Alert>

      <Grid>
        <Grid.Col span={{ base: 12, md: 8 }}>
          <MainSection detail={detail} />
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 4 }}>
          <Stack>
            {application.status !== "draft" && (
              <Card withBorder>
                <Title order={5} mb="sm">
                  Этапы проверки
                </Title>
                <PipelineSteps steps={application.pipeline_steps} />
              </Card>
            )}
            <Card withBorder>
              <Title order={5} mb="sm">
                История заявки
              </Title>
              {events.data ? <EventsTimeline events={events.data} /> : <PageLoader />}
            </Card>
          </Stack>
        </Grid.Col>
      </Grid>
    </Stack>
  );
}
