## very rough version to try mimic issue in a controlled environment

- for debugging https://github.com/hashicorp/nomad/issues/24339
- requires local running dockerd ⚠️ (as docker-dind is challenging) 
- docker compose v2

- ⬆️  docker compose up
  - _should_ bring up containers
- ℹ️  scripts/test-count
  - to check output
- ⚠️. scripts/cleanup ⚠️
  - to cleanup containers started as we are running them on the local dockerd, which wont be cleaned after stopping nomad.  
    - does so by checking containers with label=com.hashicorp.nomad.node_name=region1.dc1.client
- scripts/master-control
  - docker compose up -d 
  - waits for client to start
  - run test-count script
  - docker compose down `feel free to modify`
  - scripts/cleanup to cleanup containers

- URL to Nomad-UI: https://localhost:4646/ui/clients
 
```
example output of scripts/master-control

$ scripts/master-control
[+] Running 6/6
 ✔ Network gh-24339_hashicorp                Created                                                                                                                                                                      0.1s 
 ✔ Container gh-24339-consulserver-1         Healthy                                                                                                                                                                     13.0s 
 ✔ Container gh-24339-region1.dc1.server-1   Healthy                                                                                                                                                                     22.9s 
 ✔ Container gh-24339-region1.dc1.server3-1  Healthy                                                                                                                                                                     22.9s 
 ✔ Container gh-24339-region1.dc1.server2-1  Healthy                                                                                                                                                                     22.9s 
 ✔ Container gh-24339-region1.dc1.client-1   Started                                                                                                                                                                     23.4s 
 - - - - 
waiting for region1.dc1.client-1 to start
 - - - - 
.557cb60aa6ac   gh-24339-region1.dc1.client     "/scripts/nomad-init…"   28 seconds ago   Up 5 seconds (healthy)    127.0.0.1:4649->4649/tcp, 127.0.0.1:4653->4653/tcp, 127.0.0.1:4658->4658/tcp   gh-24339-region1.dc1.client-1
 - - - - 
region1.dc1.client-1 started check counts
 - - - - 
nomad_client_tasks_running: nomad_client_tasks_running{datacenter="dc1",node_class="none",node_id="cb16426c-7275-2175-2982-fa78e65e142d",node_pool="default",node_scheduling_eligibility="eligible",node_status="initializing"} 0
nomad_client_tasks_running{datacenter="dc1",node_class="none",node_id="cb16426c-7275-2175-2982-fa78e65e142d",node_pool="default",node_scheduling_eligibility="eligible",node_status="ready"} 0
check 1 :: counted: 0
nomad_client_tasks_running: nomad_client_tasks_running{datacenter="dc1",node_class="none",node_id="cb16426c-7275-2175-2982-fa78e65e142d",node_pool="default",node_scheduling_eligibility="eligible",node_status="initializing"} 0
nomad_client_tasks_running{datacenter="dc1",node_class="none",node_id="cb16426c-7275-2175-2982-fa78e65e142d",node_pool="default",node_scheduling_eligibility="eligible",node_status="ready"} 0
check 2 :: counted: 0
nomad_client_tasks_running: nomad_client_tasks_running{datacenter="dc1",node_class="none",node_id="cb16426c-7275-2175-2982-fa78e65e142d",node_pool="default",node_scheduling_eligibility="eligible",node_status="initializing"} 0
nomad_client_tasks_running{datacenter="dc1",node_class="none",node_id="cb16426c-7275-2175-2982-fa78e65e142d",node_pool="default",node_scheduling_eligibility="eligible",node_status="ready"} 20
nomad_client_allocs_memory_usage{alloc_id="13e57f1b-67ed-5b50-2f06-a2962cf1e45c",job="example-13",namespace="default",task="redis",task_group="cache"} 3.428352e+06
nomad_client_allocs_memory_usage{alloc_id="1d7b3fea-15ec-2e57-9c77-5718db8b64f8",job="example-15",namespace="default",task="redis",task_group="cache"} 3.428352e+06
nomad_client_allocs_memory_usage{alloc_id="21380272-253d-b250-b782-837a33af3994",job="example-7",namespace="default",task="redis",task_group="cache"} 3.424256e+06
nomad_client_allocs_memory_usage{alloc_id="5985f8e9-d83a-2ebe-cd9c-e7450a148f36",job="example-18",namespace="default",task="redis",task_group="cache"} 802816
nomad_client_allocs_memory_usage{alloc_id="6284f9b6-5a5c-af6c-211a-7a7bdfb943db",job="example-9",namespace="default",task="redis",task_group="cache"} 3.424256e+06
nomad_client_allocs_memory_usage{alloc_id="69a4fce1-678a-507f-8588-42d3e60c5b45",job="example-6",namespace="default",task="redis",task_group="cache"} 3.428352e+06
nomad_client_allocs_memory_usage{alloc_id="6a59a228-5e81-8108-6072-f0b7f8d43a2f",job="example-10",namespace="default",task="redis",task_group="cache"} 3.424256e+06
nomad_client_allocs_memory_usage{alloc_id="75804212-63ef-f942-e10f-e343e9027ec6",job="example-14",namespace="default",task="redis",task_group="cache"} 3.424256e+06
nomad_client_allocs_memory_usage{alloc_id="858ae6ba-1305-a007-e274-ddaaa1f17acf",job="example-12",namespace="default",task="redis",task_group="cache"} 3.428352e+06
nomad_client_allocs_memory_usage{alloc_id="9360cfd4-a4e0-cdc5-038e-d260fca14114",job="example-11",namespace="default",task="redis",task_group="cache"} 3.428352e+06
nomad_client_allocs_memory_usage{alloc_id="9a8d6044-947a-f028-36f7-e60d2548908c",job="example-20",namespace="default",task="redis",task_group="cache"} 3.416064e+06
nomad_client_allocs_memory_usage{alloc_id="a9253a99-0ab1-546c-166e-fc9b89824f5b",job="example-16",namespace="default",task="redis",task_group="cache"} 3.424256e+06
nomad_client_allocs_memory_usage{alloc_id="adb4e6eb-dffc-92f8-55c0-87ff73a4189c",job="example-2",namespace="default",task="redis",task_group="cache"} 3.42016e+06
nomad_client_allocs_memory_usage{alloc_id="b503021e-86b7-641d-1e3c-ec79ecd613b0",job="example-3",namespace="default",task="redis",task_group="cache"} 3.424256e+06
nomad_client_allocs_memory_usage{alloc_id="b540c9b0-1418-b7b6-ee7c-28e5a4f13a15",job="example-1",namespace="default",task="redis",task_group="cache"} 3.424256e+06
nomad_client_allocs_memory_usage{alloc_id="bf0fbc9d-636f-200a-46b9-18b0398b55ea",job="example-8",namespace="default",task="redis",task_group="cache"} 3.428352e+06
nomad_client_allocs_memory_usage{alloc_id="d15fd25c-84d3-8281-9b88-5aef8f529c07",job="example-17",namespace="default",task="redis",task_group="cache"} 3.424256e+06
nomad_client_allocs_memory_usage{alloc_id="d69819f3-1a02-fded-9e42-a3d250233873",job="example-4",namespace="default",task="redis",task_group="cache"} 3.424256e+06
nomad_client_allocs_memory_usage{alloc_id="da2a80b4-bdf2-8cba-b4e4-55e83f54828f",job="example-5",namespace="default",task="redis",task_group="cache"} 3.432448e+06
nomad_client_allocs_memory_usage{alloc_id="e82e6846-7716-5608-8e53-1fd1b69b1cc1",job="example-19",namespace="default",task="redis",task_group="cache"} 3.424256e+06
check 3 :: counted: 20
nomad_client_tasks_running: nomad_client_tasks_running{datacenter="dc1",node_class="none",node_id="cb16426c-7275-2175-2982-fa78e65e142d",node_pool="default",node_scheduling_eligibility="eligible",node_status="initializing"} 0
nomad_client_tasks_running{datacenter="dc1",node_class="none",node_id="cb16426c-7275-2175-2982-fa78e65e142d",node_pool="default",node_scheduling_eligibility="eligible",node_status="ready"} 20
nomad_client_allocs_memory_usage{alloc_id="13e57f1b-67ed-5b50-2f06-a2962cf1e45c",job="example-13",namespace="default",task="redis",task_group="cache"} 3.428352e+06
nomad_client_allocs_memory_usage{alloc_id="1d7b3fea-15ec-2e57-9c77-5718db8b64f8",job="example-15",namespace="default",task="redis",task_group="cache"} 3.428352e+06
nomad_client_allocs_memory_usage{alloc_id="21380272-253d-b250-b782-837a33af3994",job="example-7",namespace="default",task="redis",task_group="cache"} 3.424256e+06
nomad_client_allocs_memory_usage{alloc_id="5985f8e9-d83a-2ebe-cd9c-e7450a148f36",job="example-18",namespace="default",task="redis",task_group="cache"} 802816
nomad_client_allocs_memory_usage{alloc_id="6284f9b6-5a5c-af6c-211a-7a7bdfb943db",job="example-9",namespace="default",task="redis",task_group="cache"} 3.424256e+06
nomad_client_allocs_memory_usage{alloc_id="69a4fce1-678a-507f-8588-42d3e60c5b45",job="example-6",namespace="default",task="redis",task_group="cache"} 3.428352e+06
nomad_client_allocs_memory_usage{alloc_id="6a59a228-5e81-8108-6072-f0b7f8d43a2f",job="example-10",namespace="default",task="redis",task_group="cache"} 3.424256e+06
nomad_client_allocs_memory_usage{alloc_id="75804212-63ef-f942-e10f-e343e9027ec6",job="example-14",namespace="default",task="redis",task_group="cache"} 3.424256e+06
nomad_client_allocs_memory_usage{alloc_id="858ae6ba-1305-a007-e274-ddaaa1f17acf",job="example-12",namespace="default",task="redis",task_group="cache"} 3.428352e+06
nomad_client_allocs_memory_usage{alloc_id="9360cfd4-a4e0-cdc5-038e-d260fca14114",job="example-11",namespace="default",task="redis",task_group="cache"} 3.428352e+06
nomad_client_allocs_memory_usage{alloc_id="9a8d6044-947a-f028-36f7-e60d2548908c",job="example-20",namespace="default",task="redis",task_group="cache"} 3.416064e+06
nomad_client_allocs_memory_usage{alloc_id="a9253a99-0ab1-546c-166e-fc9b89824f5b",job="example-16",namespace="default",task="redis",task_group="cache"} 3.424256e+06
nomad_client_allocs_memory_usage{alloc_id="adb4e6eb-dffc-92f8-55c0-87ff73a4189c",job="example-2",namespace="default",task="redis",task_group="cache"} 3.42016e+06
nomad_client_allocs_memory_usage{alloc_id="b503021e-86b7-641d-1e3c-ec79ecd613b0",job="example-3",namespace="default",task="redis",task_group="cache"} 3.424256e+06
nomad_client_allocs_memory_usage{alloc_id="b540c9b0-1418-b7b6-ee7c-28e5a4f13a15",job="example-1",namespace="default",task="redis",task_group="cache"} 3.424256e+06
nomad_client_allocs_memory_usage{alloc_id="bf0fbc9d-636f-200a-46b9-18b0398b55ea",job="example-8",namespace="default",task="redis",task_group="cache"} 3.428352e+06
nomad_client_allocs_memory_usage{alloc_id="d15fd25c-84d3-8281-9b88-5aef8f529c07",job="example-17",namespace="default",task="redis",task_group="cache"} 3.424256e+06
nomad_client_allocs_memory_usage{alloc_id="d69819f3-1a02-fded-9e42-a3d250233873",job="example-4",namespace="default",task="redis",task_group="cache"} 3.424256e+06
nomad_client_allocs_memory_usage{alloc_id="da2a80b4-bdf2-8cba-b4e4-55e83f54828f",job="example-5",namespace="default",task="redis",task_group="cache"} 3.432448e+06
nomad_client_allocs_memory_usage{alloc_id="e82e6846-7716-5608-8e53-1fd1b69b1cc1",job="example-19",namespace="default",task="redis",task_group="cache"} 3.424256e+06
check 4 :: counted: 20
nomad_client_tasks_running: nomad_client_tasks_running{datacenter="dc1",node_class="none",node_id="cb16426c-7275-2175-2982-fa78e65e142d",node_pool="default",node_scheduling_eligibility="eligible",node_status="ready"} 20
nomad_client_allocs_memory_usage{alloc_id="13e57f1b-67ed-5b50-2f06-a2962cf1e45c",job="example-13",namespace="default",task="redis",task_group="cache"} 3.428352e+06
nomad_client_allocs_memory_usage{alloc_id="1d7b3fea-15ec-2e57-9c77-5718db8b64f8",job="example-15",namespace="default",task="redis",task_group="cache"} 3.428352e+06
nomad_client_allocs_memory_usage{alloc_id="21380272-253d-b250-b782-837a33af3994",job="example-7",namespace="default",task="redis",task_group="cache"} 3.424256e+06
nomad_client_allocs_memory_usage{alloc_id="5985f8e9-d83a-2ebe-cd9c-e7450a148f36",job="example-18",namespace="default",task="redis",task_group="cache"} 802816
nomad_client_allocs_memory_usage{alloc_id="6284f9b6-5a5c-af6c-211a-7a7bdfb943db",job="example-9",namespace="default",task="redis",task_group="cache"} 3.424256e+06
nomad_client_allocs_memory_usage{alloc_id="69a4fce1-678a-507f-8588-42d3e60c5b45",job="example-6",namespace="default",task="redis",task_group="cache"} 3.428352e+06
nomad_client_allocs_memory_usage{alloc_id="6a59a228-5e81-8108-6072-f0b7f8d43a2f",job="example-10",namespace="default",task="redis",task_group="cache"} 3.424256e+06
nomad_client_allocs_memory_usage{alloc_id="75804212-63ef-f942-e10f-e343e9027ec6",job="example-14",namespace="default",task="redis",task_group="cache"} 3.424256e+06
nomad_client_allocs_memory_usage{alloc_id="858ae6ba-1305-a007-e274-ddaaa1f17acf",job="example-12",namespace="default",task="redis",task_group="cache"} 3.428352e+06
nomad_client_allocs_memory_usage{alloc_id="9360cfd4-a4e0-cdc5-038e-d260fca14114",job="example-11",namespace="default",task="redis",task_group="cache"} 3.428352e+06
nomad_client_allocs_memory_usage{alloc_id="9a8d6044-947a-f028-36f7-e60d2548908c",job="example-20",namespace="default",task="redis",task_group="cache"} 3.416064e+06
nomad_client_allocs_memory_usage{alloc_id="a9253a99-0ab1-546c-166e-fc9b89824f5b",job="example-16",namespace="default",task="redis",task_group="cache"} 3.424256e+06
nomad_client_allocs_memory_usage{alloc_id="adb4e6eb-dffc-92f8-55c0-87ff73a4189c",job="example-2",namespace="default",task="redis",task_group="cache"} 3.42016e+06
nomad_client_allocs_memory_usage{alloc_id="b503021e-86b7-641d-1e3c-ec79ecd613b0",job="example-3",namespace="default",task="redis",task_group="cache"} 3.424256e+06
nomad_client_allocs_memory_usage{alloc_id="b540c9b0-1418-b7b6-ee7c-28e5a4f13a15",job="example-1",namespace="default",task="redis",task_group="cache"} 3.424256e+06
nomad_client_allocs_memory_usage{alloc_id="bf0fbc9d-636f-200a-46b9-18b0398b55ea",job="example-8",namespace="default",task="redis",task_group="cache"} 3.428352e+06
nomad_client_allocs_memory_usage{alloc_id="d15fd25c-84d3-8281-9b88-5aef8f529c07",job="example-17",namespace="default",task="redis",task_group="cache"} 3.424256e+06
nomad_client_allocs_memory_usage{alloc_id="d69819f3-1a02-fded-9e42-a3d250233873",job="example-4",namespace="default",task="redis",task_group="cache"} 3.424256e+06
nomad_client_allocs_memory_usage{alloc_id="da2a80b4-bdf2-8cba-b4e4-55e83f54828f",job="example-5",namespace="default",task="redis",task_group="cache"} 3.432448e+06
nomad_client_allocs_memory_usage{alloc_id="e82e6846-7716-5608-8e53-1fd1b69b1cc1",job="example-19",namespace="default",task="redis",task_group="cache"} 3.424256e+06
check 5 :: counted: 20
nomad_client_tasks_running: nomad_client_tasks_running{datacenter="dc1",node_class="none",node_id="cb16426c-7275-2175-2982-fa78e65e142d",node_pool="default",node_scheduling_eligibility="eligible",node_status="ready"} 20
nomad_client_allocs_memory_usage{alloc_id="13e57f1b-67ed-5b50-2f06-a2962cf1e45c",job="example-13",namespace="default",task="redis",task_group="cache"} 3.428352e+06
nomad_client_allocs_memory_usage{alloc_id="1d7b3fea-15ec-2e57-9c77-5718db8b64f8",job="example-15",namespace="default",task="redis",task_group="cache"} 3.428352e+06
nomad_client_allocs_memory_usage{alloc_id="21380272-253d-b250-b782-837a33af3994",job="example-7",namespace="default",task="redis",task_group="cache"} 3.424256e+06
nomad_client_allocs_memory_usage{alloc_id="5985f8e9-d83a-2ebe-cd9c-e7450a148f36",job="example-18",namespace="default",task="redis",task_group="cache"} 802816
nomad_client_allocs_memory_usage{alloc_id="6284f9b6-5a5c-af6c-211a-7a7bdfb943db",job="example-9",namespace="default",task="redis",task_group="cache"} 3.424256e+06
nomad_client_allocs_memory_usage{alloc_id="69a4fce1-678a-507f-8588-42d3e60c5b45",job="example-6",namespace="default",task="redis",task_group="cache"} 3.428352e+06
nomad_client_allocs_memory_usage{alloc_id="6a59a228-5e81-8108-6072-f0b7f8d43a2f",job="example-10",namespace="default",task="redis",task_group="cache"} 3.424256e+06
nomad_client_allocs_memory_usage{alloc_id="75804212-63ef-f942-e10f-e343e9027ec6",job="example-14",namespace="default",task="redis",task_group="cache"} 3.424256e+06
nomad_client_allocs_memory_usage{alloc_id="858ae6ba-1305-a007-e274-ddaaa1f17acf",job="example-12",namespace="default",task="redis",task_group="cache"} 3.428352e+06
nomad_client_allocs_memory_usage{alloc_id="9360cfd4-a4e0-cdc5-038e-d260fca14114",job="example-11",namespace="default",task="redis",task_group="cache"} 3.428352e+06
nomad_client_allocs_memory_usage{alloc_id="9a8d6044-947a-f028-36f7-e60d2548908c",job="example-20",namespace="default",task="redis",task_group="cache"} 3.416064e+06
nomad_client_allocs_memory_usage{alloc_id="a9253a99-0ab1-546c-166e-fc9b89824f5b",job="example-16",namespace="default",task="redis",task_group="cache"} 3.424256e+06
nomad_client_allocs_memory_usage{alloc_id="adb4e6eb-dffc-92f8-55c0-87ff73a4189c",job="example-2",namespace="default",task="redis",task_group="cache"} 3.42016e+06
nomad_client_allocs_memory_usage{alloc_id="b503021e-86b7-641d-1e3c-ec79ecd613b0",job="example-3",namespace="default",task="redis",task_group="cache"} 3.424256e+06
nomad_client_allocs_memory_usage{alloc_id="b540c9b0-1418-b7b6-ee7c-28e5a4f13a15",job="example-1",namespace="default",task="redis",task_group="cache"} 3.424256e+06
nomad_client_allocs_memory_usage{alloc_id="bf0fbc9d-636f-200a-46b9-18b0398b55ea",job="example-8",namespace="default",task="redis",task_group="cache"} 3.428352e+06
nomad_client_allocs_memory_usage{alloc_id="d15fd25c-84d3-8281-9b88-5aef8f529c07",job="example-17",namespace="default",task="redis",task_group="cache"} 3.424256e+06
nomad_client_allocs_memory_usage{alloc_id="d69819f3-1a02-fded-9e42-a3d250233873",job="example-4",namespace="default",task="redis",task_group="cache"} 3.424256e+06
nomad_client_allocs_memory_usage{alloc_id="da2a80b4-bdf2-8cba-b4e4-55e83f54828f",job="example-5",namespace="default",task="redis",task_group="cache"} 3.432448e+06
nomad_client_allocs_memory_usage{alloc_id="e82e6846-7716-5608-8e53-1fd1b69b1cc1",job="example-19",namespace="default",task="redis",task_group="cache"} 3.424256e+06
check 6 :: counted: 20
nomad_client_tasks_running: nomad_client_tasks_running{datacenter="dc1",node_class="none",node_id="cb16426c-7275-2175-2982-fa78e65e142d",node_pool="default",node_scheduling_eligibility="eligible",node_status="ready"} 20
nomad_client_allocs_memory_usage{alloc_id="1d7b3fea-15ec-2e57-9c77-5718db8b64f8",job="example-15",namespace="default",task="redis",task_group="cache"} 3.428352e+06
nomad_client_allocs_memory_usage{alloc_id="6284f9b6-5a5c-af6c-211a-7a7bdfb943db",job="example-9",namespace="default",task="redis",task_group="cache"} 3.424256e+06
nomad_client_allocs_memory_usage{alloc_id="69a4fce1-678a-507f-8588-42d3e60c5b45",job="example-6",namespace="default",task="redis",task_group="cache"} 3.428352e+06
nomad_client_allocs_memory_usage{alloc_id="6a59a228-5e81-8108-6072-f0b7f8d43a2f",job="example-10",namespace="default",task="redis",task_group="cache"} 3.424256e+06
nomad_client_allocs_memory_usage{alloc_id="9a8d6044-947a-f028-36f7-e60d2548908c",job="example-20",namespace="default",task="redis",task_group="cache"} 0
nomad_client_allocs_memory_usage{alloc_id="a9253a99-0ab1-546c-166e-fc9b89824f5b",job="example-16",namespace="default",task="redis",task_group="cache"} 3.424256e+06
nomad_client_allocs_memory_usage{alloc_id="adb4e6eb-dffc-92f8-55c0-87ff73a4189c",job="example-2",namespace="default",task="redis",task_group="cache"} 3.42016e+06
nomad_client_allocs_memory_usage{alloc_id="b540c9b0-1418-b7b6-ee7c-28e5a4f13a15",job="example-1",namespace="default",task="redis",task_group="cache"} 0
nomad_client_allocs_memory_usage{alloc_id="d15fd25c-84d3-8281-9b88-5aef8f529c07",job="example-17",namespace="default",task="redis",task_group="cache"} 3.424256e+06
nomad_client_allocs_memory_usage{alloc_id="d69819f3-1a02-fded-9e42-a3d250233873",job="example-4",namespace="default",task="redis",task_group="cache"} 0
nomad_client_allocs_memory_usage{alloc_id="e82e6846-7716-5608-8e53-1fd1b69b1cc1",job="example-19",namespace="default",task="redis",task_group="cache"} 3.424256e+06
check 7 :: counted: 11
nomad_client_tasks_running: nomad_client_tasks_running{datacenter="dc1",node_class="none",node_id="cb16426c-7275-2175-2982-fa78e65e142d",node_pool="default",node_scheduling_eligibility="eligible",node_status="ready"} 20
nomad_client_allocs_memory_usage{alloc_id="9a8d6044-947a-f028-36f7-e60d2548908c",job="example-20",namespace="default",task="redis",task_group="cache"} 0
nomad_client_allocs_memory_usage{alloc_id="b540c9b0-1418-b7b6-ee7c-28e5a4f13a15",job="example-1",namespace="default",task="redis",task_group="cache"} 0
nomad_client_allocs_memory_usage{alloc_id="d69819f3-1a02-fded-9e42-a3d250233873",job="example-4",namespace="default",task="redis",task_group="cache"} 0
check 8 :: counted: 3
nomad_client_tasks_running: nomad_client_tasks_running{datacenter="dc1",node_class="none",node_id="cb16426c-7275-2175-2982-fa78e65e142d",node_pool="default",node_scheduling_eligibility="eligible",node_status="ready"} 20
nomad_client_allocs_memory_usage{alloc_id="9a8d6044-947a-f028-36f7-e60d2548908c",job="example-20",namespace="default",task="redis",task_group="cache"} 0
nomad_client_allocs_memory_usage{alloc_id="b540c9b0-1418-b7b6-ee7c-28e5a4f13a15",job="example-1",namespace="default",task="redis",task_group="cache"} 0
nomad_client_allocs_memory_usage{alloc_id="d69819f3-1a02-fded-9e42-a3d250233873",job="example-4",namespace="default",task="redis",task_group="cache"} 0
check 9 :: counted: 3
nomad_client_tasks_running: nomad_client_tasks_running{datacenter="dc1",node_class="none",node_id="cb16426c-7275-2175-2982-fa78e65e142d",node_pool="default",node_scheduling_eligibility="eligible",node_status="ready"} 20
nomad_client_allocs_memory_usage{alloc_id="9a8d6044-947a-f028-36f7-e60d2548908c",job="example-20",namespace="default",task="redis",task_group="cache"} 0
nomad_client_allocs_memory_usage{alloc_id="b540c9b0-1418-b7b6-ee7c-28e5a4f13a15",job="example-1",namespace="default",task="redis",task_group="cache"} 0
nomad_client_allocs_memory_usage{alloc_id="d69819f3-1a02-fded-9e42-a3d250233873",job="example-4",namespace="default",task="redis",task_group="cache"} 0
check 10 :: counted: 3
nomad_client_tasks_running: nomad_client_tasks_running{datacenter="dc1",node_class="none",node_id="cb16426c-7275-2175-2982-fa78e65e142d",node_pool="default",node_scheduling_eligibility="eligible",node_status="ready"} 20
check 11 :: counted: 0
nomad_client_tasks_running: nomad_client_tasks_running{datacenter="dc1",node_class="none",node_id="cb16426c-7275-2175-2982-fa78e65e142d",node_pool="default",node_scheduling_eligibility="eligible",node_status="ready"} 20
check 12 :: counted: 0
nomad_client_tasks_running: nomad_client_tasks_running{datacenter="dc1",node_class="none",node_id="cb16426c-7275-2175-2982-fa78e65e142d",node_pool="default",node_scheduling_eligibility="eligible",node_status="ready"} 20
nomad_client_allocs_memory_usage{alloc_id="e82e6846-7716-5608-8e53-1fd1b69b1cc1",job="example-19",namespace="default",task="redis",task_group="cache"} 0
check 13 :: counted: 1
nomad_client_tasks_running: nomad_client_tasks_running{datacenter="dc1",node_class="none",node_id="cb16426c-7275-2175-2982-fa78e65e142d",node_pool="default",node_scheduling_eligibility="eligible",node_status="ready"} 20
nomad_client_allocs_memory_usage{alloc_id="e82e6846-7716-5608-8e53-1fd1b69b1cc1",job="example-19",namespace="default",task="redis",task_group="cache"} 0
check 14 :: counted: 1
nomad_client_tasks_running: nomad_client_tasks_running{datacenter="dc1",node_class="none",node_id="cb16426c-7275-2175-2982-fa78e65e142d",node_pool="default",node_scheduling_eligibility="eligible",node_status="ready"} 20
nomad_client_allocs_memory_usage{alloc_id="9360cfd4-a4e0-cdc5-038e-d260fca14114",job="example-11",namespace="default",task="redis",task_group="cache"} 0
nomad_client_allocs_memory_usage{alloc_id="bf0fbc9d-636f-200a-46b9-18b0398b55ea",job="example-8",namespace="default",task="redis",task_group="cache"} 0
nomad_client_allocs_memory_usage{alloc_id="e82e6846-7716-5608-8e53-1fd1b69b1cc1",job="example-19",namespace="default",task="redis",task_group="cache"} 0
check 15 :: counted: 3
nomad_client_tasks_running: nomad_client_tasks_running{datacenter="dc1",node_class="none",node_id="cb16426c-7275-2175-2982-fa78e65e142d",node_pool="default",node_scheduling_eligibility="eligible",node_status="ready"} 20
nomad_client_allocs_memory_usage{alloc_id="9360cfd4-a4e0-cdc5-038e-d260fca14114",job="example-11",namespace="default",task="redis",task_group="cache"} 0
nomad_client_allocs_memory_usage{alloc_id="bf0fbc9d-636f-200a-46b9-18b0398b55ea",job="example-8",namespace="default",task="redis",task_group="cache"} 0
nomad_client_allocs_memory_usage{alloc_id="e82e6846-7716-5608-8e53-1fd1b69b1cc1",job="example-19",namespace="default",task="redis",task_group="cache"} 0
check 16 :: counted: 3
nomad_client_tasks_running: nomad_client_tasks_running{datacenter="dc1",node_class="none",node_id="cb16426c-7275-2175-2982-fa78e65e142d",node_pool="default",node_scheduling_eligibility="eligible",node_status="ready"} 20
nomad_client_allocs_memory_usage{alloc_id="9360cfd4-a4e0-cdc5-038e-d260fca14114",job="example-11",namespace="default",task="redis",task_group="cache"} 0
nomad_client_allocs_memory_usage{alloc_id="bf0fbc9d-636f-200a-46b9-18b0398b55ea",job="example-8",namespace="default",task="redis",task_group="cache"} 0
check 17 :: counted: 2
nomad_client_tasks_running: nomad_client_tasks_running{datacenter="dc1",node_class="none",node_id="cb16426c-7275-2175-2982-fa78e65e142d",node_pool="default",node_scheduling_eligibility="eligible",node_status="ready"} 20
nomad_client_allocs_memory_usage{alloc_id="75804212-63ef-f942-e10f-e343e9027ec6",job="example-14",namespace="default",task="redis",task_group="cache"} 0
nomad_client_allocs_memory_usage{alloc_id="9360cfd4-a4e0-cdc5-038e-d260fca14114",job="example-11",namespace="default",task="redis",task_group="cache"} 0
nomad_client_allocs_memory_usage{alloc_id="bf0fbc9d-636f-200a-46b9-18b0398b55ea",job="example-8",namespace="default",task="redis",task_group="cache"} 0
nomad_client_allocs_memory_usage{alloc_id="da2a80b4-bdf2-8cba-b4e4-55e83f54828f",job="example-5",namespace="default",task="redis",task_group="cache"} 0
check 18 :: counted: 4
nomad_client_tasks_running: nomad_client_tasks_running{datacenter="dc1",node_class="none",node_id="cb16426c-7275-2175-2982-fa78e65e142d",node_pool="default",node_scheduling_eligibility="eligible",node_status="ready"} 20
nomad_client_allocs_memory_usage{alloc_id="75804212-63ef-f942-e10f-e343e9027ec6",job="example-14",namespace="default",task="redis",task_group="cache"} 0
nomad_client_allocs_memory_usage{alloc_id="da2a80b4-bdf2-8cba-b4e4-55e83f54828f",job="example-5",namespace="default",task="redis",task_group="cache"} 0
check 19 :: counted: 2
nomad_client_tasks_running: nomad_client_tasks_running{datacenter="dc1",node_class="none",node_id="cb16426c-7275-2175-2982-fa78e65e142d",node_pool="default",node_scheduling_eligibility="eligible",node_status="ready"} 20
nomad_client_allocs_memory_usage{alloc_id="75804212-63ef-f942-e10f-e343e9027ec6",job="example-14",namespace="default",task="redis",task_group="cache"} 0
nomad_client_allocs_memory_usage{alloc_id="da2a80b4-bdf2-8cba-b4e4-55e83f54828f",job="example-5",namespace="default",task="redis",task_group="cache"} 0
check 20 :: counted: 2
 - - - - 
ending test
 - - - - 
[+] Running 6/6
 ✔ Container gh-24339-region1.dc1.client-1   Removed                                                                                                                                                                      0.3s 
 ✔ Container gh-24339-region1.dc1.server3-1  Removed                                                                                                                                                                      0.4s 
 ✔ Container gh-24339-region1.dc1.server-1   Removed                                                                                                                                                                      0.5s 
 ✔ Container gh-24339-region1.dc1.server2-1  Removed                                                                                                                                                                      0.4s 
 ✔ Container gh-24339-consulserver-1         Removed                                                                                                                                                                      0.3s 
 ✔ Network gh-24339_hashicorp                Removed                                                                                                                                                                      0.2s 
54285ac40796
b3c8586e923c
9bf6709e54a8
2c8f891aa16e
f634653fe4ac
6c34ea15d972
b95a7aec8606
266946ce82d6
71b49d963265
a78413e27b8e
7466f34ff35f
867ed300545e
9c0f2e066874
ec08bc1ae449
7460c1713295
5ba7df833c01
35ea340315eb
6047cec57d73
952879cca7f2
8ce606b6b32a
54285ac40796
b3c8586e923c
9bf6709e54a8
2c8f891aa16e
f634653fe4ac
6c34ea15d972
b95a7aec8606
266946ce82d6
71b49d963265
a78413e27b8e
7466f34ff35f
867ed300545e
9c0f2e066874
ec08bc1ae449
7460c1713295
5ba7df833c01
35ea340315eb
6047cec57d73
952879cca7f2
8ce606b6b32a
Fin.

```
