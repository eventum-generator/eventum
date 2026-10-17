export interface ScenarioRow {
  name: string;
  generatorIds: string[];
  generatorCount: number;
  stuckCount: number;
  runningCount: number;
  stoppedCount: number;
  initializingCount: number;
  stoppingCount: number;
}
